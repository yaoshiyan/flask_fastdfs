from flask import request, current_app, jsonify, render_template

from utils.fdfs_client.fileUtil import *
from utils.fdfs_client.client import *
from . import uploadFile


@uploadFile.route("/uploadFile", methods=["GET", "POST"])
def uploadFile():
    if request.method == "GET":
        return render_template("uploadFile.html")
    uploadFile = request.files.get("uploadFile", '')
    file_size = getFileSize(uploadFile)
    if uploadFile and (1 < file_size < 5 * 1024 * 1024):
        hf = HandleFile(uploadFile,current_app.config)
        client_conf_obj = get_tracker_conf(hf.CLIENT_CONF)
        client = Fdfs_client(client_conf_obj)
        if hf.isImg:
            # 创建缩略图
            hf.createThumbnail()
            # 格式转为jpg bytes io
            hf.convertImgToBytesIO()
            # 保存原图(JPG格式)到fastdfs
            jpg_size = getFileSize(hf.file)
            ret1 = client.upload_by_file(hf.file,jpg_size, file_ext_name="jpg")
            # 保存缩略图(PNG格式)到fastdfs,
            if ret1["status"] == "success":
                png_size = getFileSize(hf.resizeIm)
                ret2 = client.upload_slave_by_file(hf.resizeIm,png_size, ret1['group_name'],ret1["remote_filename"],
                                                         prefix_name='_small', file_ext_name="png")
                if ret2["status"] == "success":
                    url = getFileUrl(ret2)
                    return jsonify({"err_code": 0, "image_url": url})
                else:
                    return jsonify({"err_code": -1, "image_url": ""})
            else:
                return jsonify({"err_code": -2, "image_url": ""})
        else:
            # 保存文件
            file_ext_name = get_file_ext_name(hf.fileName)
            ret3 = client.upload_by_file(hf.file, file_size, file_ext_name=file_ext_name)
            url = getFileUrl(ret3)
            if ret3["status"] == "success":
                return jsonify({"err_code": 0, "image_url": url})
            else:
                return jsonify({"err_code": -2, "image_url": ""})
    else:
        return jsonify({"err_code": -3, "image_url": ""})

