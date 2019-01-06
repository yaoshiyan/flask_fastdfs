#!/usr/bin/env python
# -*- coding: utf-8 -*-
# filename: client.py

'''
  Client module for Fastdfs 3.08
  author: scott yuan scottzer8@gmail.com
  date: 2012-06-21
'''

from utils.fdfs_client.tracker_client import *
from utils.fdfs_client.storage_client import *
from utils.fdfs_client.exceptions import *


def get_tracker_conf(conf_path='client.conf'):
    cf = Fdfs_ConfigParser()
    tracker = {}
    try:
        cf.read(conf_path)
        timeout = cf.getint('__config__', 'connect_timeout')
        tracker_list = cf.get('__config__', 'tracker_server')
        if isinstance(tracker_list, str):
            tracker_list = [tracker_list]
        tracker_ip_list = []
        for tr in tracker_list:
            tracker_ip, tracker_port = tr.split(':')
            tracker_ip_list.append(tracker_ip)
        tracker['host_tuple'] = tuple(tracker_ip_list)
        tracker['port'] = int(tracker_port)
        tracker['timeout'] = timeout
        tracker['name'] = 'Tracker Pool'
    except:
        raise
    return tracker


class Fdfs_client(object):
    '''
    Class Fdfs_client implemented Fastdfs client protol ver 3.08.

    It's useful upload, download, delete file to or from fdfs server, etc. It's uses
    connection pool to manage connection to server.
    '''

    def __init__(self, trackers, poolclass=ConnectionPool):
        self.trackers = trackers
        self.tracker_pool = poolclass(**self.trackers)
        self.timeout = self.trackers['timeout']

    def __del__(self):
        try:
            self.pool.destroy()
            self.pool = None
        except:
            pass

    def upload_by_filename(self, filename):
        '''
        Upload a file to Storage server.
        arguments:
        @filename: string, name of file that will be uploaded
        @return dict {
            'Group name'      : group_name,
            'Remote file_id'  : remote_file_id,
            'Status'          : 'Upload successed.',
            'Local file name' : local_file_name,
            'Uploaded size'   : upload_size,
            'Storage IP'      : storage_ip
        } if success else None
        '''
        isfile, errmsg = fdfs_check_file(filename)
        if not isfile:
            raise DataError(errmsg + '(uploading)')
        tc = Tracker_client(self.tracker_pool)
        store_serv = tc.tracker_query_storage_stor_without_group()
        store = Storage_client(store_serv.ip_addr, store_serv.port, self.timeout)
        return store.storage_upload_by_filename(store_serv, filename)

    def upload_by_file(self, file,file_size, file_ext_name=''):
        tc = Tracker_client(self.tracker_pool)
        store_serv = tc.tracker_query_storage_stor_without_group()
        store = Storage_client(store_serv.ip_addr, store_serv.port, self.timeout)
        return store.storage_upload_by_file(store_serv, file,file_size, file_ext_name)

    def upload_slave_by_filename(self, filename, group_name, master_filename, prefix_name=''):
        '''
        Upload slave file to Storage server.
        '''
        isfile, errmsg = fdfs_check_file(filename)
        if not isfile:
            raise DataError(errmsg + '(uploading slave)')
        tc = Tracker_client(self.tracker_pool)
        store_serv = tc.tracker_query_storage_stor_with_group(group_name)
        store = Storage_client(store_serv.ip_addr, store_serv.port, self.timeout)
        return store.storage_upload_slave_by_filename(store_serv, filename, master_filename, prefix_name)

    def upload_slave_by_file(self, filename,file_size, group_name, master_filename, prefix_name='', file_ext_name=''):
        '''
        Upload slave file to Storage server.
        '''
        tc = Tracker_client(self.tracker_pool)
        store_serv = tc.tracker_query_storage_stor_with_group(group_name)
        store = Storage_client(store_serv.ip_addr, store_serv.port, self.timeout)
        return store.storage_upload_slave_by_file(store_serv, filename,file_size, master_filename, prefix_name, file_ext_name)

    def delete_file(self, group_name, remote_filename):
        '''
        Delete a file from Storage server.
        '''
        tc = Tracker_client(self.tracker_pool)
        store_serv = tc.tracker_query_storage_update(group_name, remote_filename)
        store = Storage_client(store_serv.ip_addr, store_serv.port, self.timeout)
        return store.storage_delete_file(store_serv, remote_filename)

    def download_to_file(self, local_filename, group_name, remote_filename, offset=0, down_bytes=0):
        '''
        Download a file from Storage server.
        '''
        if not offset:
            file_offset = int(offset)
        if not down_bytes:
            download_bytes = int(down_bytes)
        tc = Tracker_client(self.tracker_pool)
        store_serv = tc.tracker_query_storage_fetch(group_name, remote_filename)
        store = Storage_client(store_serv.ip_addr, store_serv.port, self.timeout)
        return store.storage_download_to_file(tc, store_serv, local_filename, file_offset, download_bytes,
                                              remote_filename)

    def list_one_group(self, group_name):
        '''
        List one group information.
        arguments:
        @group_name: string, group name will be list
        @return Group_info,  instance
        '''
        tc = Tracker_client(self.tracker_pool)
        return tc.tracker_list_one_group(group_name)

    def list_servers(self, group_name, storage_ip=None):
        '''
        List all storage servers information in a group
        arguments:
        @group_name: string
        @return dictionary {
            'Group name' : group_name,
            'Servers'    : server list,
        }
        '''
        tc = Tracker_client(self.tracker_pool)
        return tc.tracker_list_servers(group_name, storage_ip)

    def list_all_groups(self):
        '''
        List all group information.
        @return dictionary {
            'Groups count' : group_count,
            'Groups'       : list of groups
        }
        '''
        tc = Tracker_client(self.tracker_pool)
        return tc.tracker_list_all_groups()

    def truncate_file(self, truncated_filesize, appender_fileid):
        '''
        Truncate file in Storage server.
        arguments:
        @truncated_filesize: long
        @appender_fileid: remote_fileid
        @return: dictionary {
            'Status'     : 'Truncate successed.',
            'Storage IP' : storage_ip
        }
        '''
        trunc_filesize = int(truncated_filesize)
        tmp = split_remote_fileid(appender_fileid)
        if not tmp:
            raise DataError('[-] Error: appender_fileid is invalid.(truncate)')
        group_name, appender_filename = tmp
        tc = Tracker_client(self.tracker_pool)
        store_serv = tc.tracker_query_storage_update(group_name, appender_filename)
        store = Storage_client(store_serv.ip_addr, store_serv.port, self.timeout)
        return store.storage_truncate_file(tc, store_serv, trunc_filesize, appender_filename)
