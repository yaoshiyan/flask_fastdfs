#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename: storage_client.py


import errno

from utils.fdfs_client.fdfs_protol import *
from utils.fdfs_client.connection import *
from utils.fdfs_client.exceptions import (
    FDFSError,
    ConnectionError,
    ResponseError,
    InvaildResponse,
    DataError
)
from utils.fdfs_client.tools import *

__os_sep__ = "/" if platform.system() == 'Windows' else os.sep


def tcp_send_file(conn, filename, buffer_size=8*1024):
    '''
    Send file to server, and split into multiple pkgs while sending.
    arguments:
    @conn: connection
    @filename: string
    @buffer_size: int ,send buffer size
    @Return int: file size if success else raise ConnectionError.
    '''
    file_size = 0
    with open(filename, 'rb') as f:
        while 1:
            try:
                send_buffer = f.read(buffer_size)
                send_size = len(send_buffer)
                if send_size == 0:
                    break
                tcp_send_data(conn, send_buffer)
                file_size += send_size
            except ConnectionError as e:
                raise ConnectionError('[-] Error while uploading file(%s).' % e.args)
            except IOError as e:
                raise DataError('[-] Error while reading local file(%s).' % e.args)
    return file_size


def tcp_send_file_ex(conn, file, buffer_size=8*1024):
    file_size = 0
    file.seek(0)
    while 1:
        try:
            send_buffer = file.read(buffer_size)
            send_size = len(send_buffer)
            if send_size == 0:
                file.close()
                break
            tcp_send_data(conn, send_buffer)
            file_size += send_size
        except ConnectionError as e:
            raise ConnectionError('[-] Error while uploading file(%s).' % e.args)
        except IOError as e:
            raise DataError('[-] Error while reading local file(%s).' % e.args)
    return file_size


def tcp_recv_file(conn, local_filename, file_size, buffer_size=1024):
    '''
    Receive file from server, fragmented it while receiving and write to disk.
    arguments:
    @conn: connection
    @local_filename: string
    @file_size: int, remote file size
    @buffer_size: int, receive buffer size
    @Return int: file size if success else raise ConnectionError.
    '''
    total_file_size = 0
    flush_size = 0
    remain_bytes = file_size
    with open(local_filename, 'wb+') as f:
        while remain_bytes > 0:
            try:
                if remain_bytes >= buffer_size:
                    file_buffer, recv_size = tcp_recv_response(conn, buffer_size, buffer_size)
                else:
                    file_buffer, recv_size = tcp_recv_response(conn, remain_bytes, buffer_size)
                f.write(file_buffer)
                remain_bytes -= buffer_size
                total_file_size += recv_size
                flush_size += recv_size
                if flush_size >= 4096:
                    f.flush()
                    flush_size = 0
            except ConnectionError as e:
                raise ConnectionError('[-] Error: while downloading file(%s).' % e.args)
            except IOError as e:
                raise DataError('[-] Error: while writting local file(%s).' % e.args)
    return total_file_size


class Storage_client(object):
    '''
    The Class Storage_client for storage server.
    Note: argument host_tuple of storage server ip address, that should be a single element.
    '''

    def __init__(self, *kwargs):
        conn_kwargs = {
            'name': 'Storage Pool',
            'host_tuple': (kwargs[0],),
            'port': kwargs[1],
            'timeout': kwargs[2]
        }
        self.pool = ConnectionPool(**conn_kwargs)

    def __del__(self):
        try:
            self.pool.destroy()
            self.pool = None
        except:
            pass

    def update_pool(self, old_store_serv, new_store_serv, timeout=30):
        '''
        Update connection pool of storage client.
        We need update connection pool of storage client, while storage server is changed.
        but if server not changed, we do nothing.
        '''
        if old_store_serv.ip_addr == new_store_serv.ip_addr:
            return None
        self.pool.destroy()
        conn_kwargs = {
            'name': 'Storage_pool',
            'host_tuple': (new_store_serv.ip_addr,),
            'port': new_store_serv.port,
            'timeout': timeout
        }
        self.pool = ConnectionPool(**conn_kwargs)
        return True

    def _storage_do_upload_file(self, store_serv, file_buffer, file_size, upload_type,
                                cmd, master_filename='', prefix_name='', file_ext_name=''):
        '''
        core of upload file.
        arguments:
        @tracker_client: Tracker_client, it is useful connect to tracker server
        @store_serv: Storage_server, it is return from query tracker server
        @file_buffer: string, file name or file buffer for send
        @file_size: int
        @upload_type: int, optional: FDFS_UPLOAD_BY_FILE, FDFS_UPLOAD_BY_FILENAME,
                                     FDFS_UPLOAD_BY_BUFFER
        @meta_dic: dictionary, store metadata in it
        @cmd: int, reference fdfs protol
        @master_filename: string, useful upload slave file
        @prefix_name: string
        @file_ext_name: string
        @Return dictionary
                {
            'status': 'success',
            'group_name': group_name,
            'remote_filename': remote_filename,
            'storage_ip': store_serv.ip_addr,
            'send_file_size':send_file_size
        }

        '''

        store_conn = self.pool.get_connection()
        th = Tracker_header()
        master_filename_len = len(master_filename) if master_filename else 0
        upload_slave = len(store_serv.group_name) and master_filename_len
        prefix_name = str(prefix_name) if prefix_name else ''
        file_ext_name = str(file_ext_name) if file_ext_name else ''
        non_slave_fmt = '!B Q %ds' % FDFS_FILE_EXT_NAME_MAX_LEN
        slave_fmt = '!Q Q %ds %ds %ds' % (FDFS_FILE_PREFIX_MAX_LEN, FDFS_FILE_EXT_NAME_MAX_LEN, master_filename_len)
        th.pkg_len = struct.calcsize(slave_fmt) if upload_slave else struct.calcsize(non_slave_fmt)
        th.pkg_len += file_size
        th.cmd = cmd
        th.send_header(store_conn)
        if upload_slave:
            send_buffer = struct.pack(slave_fmt, master_filename_len, file_size,
                                      prefix_name.encode(), file_ext_name.encode(), master_filename.encode())
        else:
            send_buffer = struct.pack(non_slave_fmt, store_serv.store_path_index, file_size, file_ext_name.encode())
        try:
            tcp_send_data(store_conn, send_buffer)
            if upload_type == FDFS_UPLOAD_BY_FILENAME:
                send_file_size = tcp_send_file(store_conn, file_buffer)
            elif upload_type == FDFS_UPLOAD_BY_FILE:
                send_file_size = tcp_send_file_ex(store_conn, file_buffer)
            th.recv_header(store_conn)
            if th.status != 0:
                raise DataError('[-] Error: %d, %s' % (th.status, os.strerror(th.status)))
            recv_buffer, recv_size = tcp_recv_response(store_conn, th.pkg_len)
            if recv_size <= FDFS_GROUP_NAME_MAX_LEN:
                errmsg = '[-] Error: Storage response length is not match, '
                errmsg += 'expect: %d, actual: %d' % (th.pkg_len, recv_size)
                raise ResponseError(errmsg)
            recv_fmt = '!%ds %ds' % (FDFS_GROUP_NAME_MAX_LEN, th.pkg_len - FDFS_GROUP_NAME_MAX_LEN)
            group_name, remote_filename = bytesListToStrList(struct.unpack(recv_fmt, recv_buffer))
        except:
            raise
        finally:
            self.pool.release(store_conn)
        ret_dic = {
            'status': 'success',
            'group_name': group_name,
            'remote_filename': remote_filename,
            'storage_ip': store_serv.ip_addr,
            'send_file_size':send_file_size
        }
        return ret_dic

    def storage_upload_by_filename(self, store_serv, filename):
        file_size = os.stat(filename).st_size
        return self._storage_do_upload_file(store_serv, filename, file_size, FDFS_UPLOAD_BY_FILENAME,
                                            STORAGE_PROTO_CMD_UPLOAD_FILE,'','','')

    def storage_upload_by_file(self, store_serv, file, file_size,file_ext_name):
        return self._storage_do_upload_file(store_serv, file, file_size, FDFS_UPLOAD_BY_FILE,
                                            STORAGE_PROTO_CMD_UPLOAD_FILE, '', '', file_ext_name)

    def storage_upload_slave_by_filename(self, store_serv, filename, master_filename, prefix_name):
        file_size = os.stat(filename).st_size
        return self._storage_do_upload_file(store_serv, filename, file_size, FDFS_UPLOAD_BY_FILENAME,
                                            STORAGE_PROTO_CMD_UPLOAD_SLAVE_FILE, master_filename,
                                            prefix_name, '')

    def storage_upload_slave_by_file(self, store_serv, file, file_size,master_filename, prefix_name, file_ext_name):
        return self._storage_do_upload_file(store_serv, file, file_size, FDFS_UPLOAD_BY_FILE,
                                            STORAGE_PROTO_CMD_UPLOAD_SLAVE_FILE, master_filename,
                                            prefix_name, file_ext_name)

    def storage_delete_file(self, store_serv, remote_filename):
        '''
        Delete file from storage server.
        '''
        store_conn = self.pool.get_connection()
        th = Tracker_header()
        th.cmd = STORAGE_PROTO_CMD_DELETE_FILE
        file_name_len = len(remote_filename)
        th.pkg_len = FDFS_GROUP_NAME_MAX_LEN + file_name_len
        try:
            th.send_header(store_conn)
            # del_fmt: |-group_name(16)-filename(len)-|
            del_fmt = '!%ds %ds' % (FDFS_GROUP_NAME_MAX_LEN, file_name_len)
            send_buffer = struct.pack(del_fmt, store_serv.group_name.encode(), remote_filename.encode())
            tcp_send_data(store_conn, send_buffer)
            th.recv_header(store_conn)
            if th.status != 0:
                raise DataError('Error: %d, %s' % (th.status, os.strerror(th.status)))
        except:
            raise
        finally:
            self.pool.release(store_conn)
        ret_dic = {
            'status': 'success',
            'group_name': store_serv.group_name,
            'remote_filename': remote_filename,
            'Storage IP': store_serv.ip_addr
        }
        return ret_dic

    def _storage_do_download_file(self, tracker_client, store_serv, file_buffer, offset, download_size,
                                  download_type, remote_filename):
        '''
        Core of download file from storage server.
        You can choice download type, optional FDFS_DOWNLOAD_TO_FILE or
        FDFS_DOWNLOAD_TO_BUFFER. And you can choice file offset.
        @Return dictionary
            'Remote file name' : remote_filename,
            'Content' : local_filename or buffer,
            'Download size'   : download_size,
            'Storage IP'      : storage_ip
        '''
        store_conn = self.pool.get_connection()
        th = Tracker_header()
        remote_filename_len = len(remote_filename)
        th.pkg_len = FDFS_PROTO_PKG_LEN_SIZE * 2 + FDFS_GROUP_NAME_MAX_LEN + remote_filename_len
        th.cmd = STORAGE_PROTO_CMD_DOWNLOAD_FILE
        try:
            th.send_header(store_conn)
            # down_fmt: |-offset(8)-download_bytes(8)-group_name(16)-remote_filename(len)-|
            down_fmt = '!Q Q %ds %ds' % (FDFS_GROUP_NAME_MAX_LEN, remote_filename_len)
            send_buffer = struct.pack(down_fmt, offset, download_size, store_serv.group_name.encode(),
                                      remote_filename.encode())
            tcp_send_data(store_conn, send_buffer)
            th.recv_header(store_conn)
            # if th.status == 2:
            #    raise DataError('[-] Error: remote file %s is not exist.' %
            #                    (store_serv.group_name + __os_sep__.encode() + remote_filename))
            if th.status != 0:
                raise DataError('Error: %d %s' % (th.status, os.strerror(th.status)))
            if download_type == FDFS_DOWNLOAD_TO_FILE:
                total_recv_size = tcp_recv_file(store_conn, file_buffer, th.pkg_len)
            elif download_type == FDFS_DOWNLOAD_TO_BUFFER:
                recv_buffer, total_recv_size = tcp_recv_response(store_conn, th.pkg_len)
        except:
            raise
        finally:
            self.pool.release(store_conn)
        ret_dic = {
            'Remote file_id': store_serv.group_name + __os_sep__.encode() + remote_filename,
            'Content': file_buffer if download_type == FDFS_DOWNLOAD_TO_FILE else recv_buffer,
            'Download size': appromix(total_recv_size),
            'Storage IP': store_serv.ip_addr
        }
        return ret_dic

    def storage_download_to_file(self, tracker_client, store_serv, local_filename, file_offset, download_bytes,
                                 remote_filename):
        return self._storage_do_download_file(tracker_client, store_serv, local_filename, file_offset, download_bytes,
                                              FDFS_DOWNLOAD_TO_FILE, remote_filename)

    def _storage_do_truncate_file(self, tracker_client, store_serv, truncated_filesize, appender_filename):
        store_conn = self.pool.get_connection()
        th = Tracker_header()
        th.cmd = STORAGE_PROTO_CMD_TRUNCATE_FILE
        appender_filename_len = len(appender_filename)
        th.pkg_len = FDFS_PROTO_PKG_LEN_SIZE * 2 + appender_filename_len
        try:
            th.send_header(store_conn)
            # truncate_fmt:|-appender_filename_len(8)-truncate_filesize(8)
            #              -appender_filename(len)-|
            truncate_fmt = '!Q Q %ds' % appender_filename_len
            send_buffer = struct.pack(truncate_fmt, appender_filename_len, truncated_filesize,
                                      appender_filename.encode())
            tcp_send_data(store_conn, send_buffer)
            th.recv_header(store_conn)
            if th.status != 0:
                raise DataError('[-] Error: %d, %s' % (th.status, os.strerror(th.status)))
        except:
            raise
        finally:
            self.pool.release(store_conn)
        ret_dict = {}
        ret_dict['Status'] = 'Truncate successed.'
        ret_dict['Storage IP'] = store_serv.ip_addr
        return ret_dict

    def storage_truncate_file(self, tracker_client, store_serv, truncated_filesize, appender_filename):
        return self._storage_do_truncate_file(tracker_client, store_serv, truncated_filesize, appender_filename)
