# flask_fastdfs
一个flask与fastdfs分布式文件系统上传文件的案例，支持py3

utils/fdfs_client 是由py3Fdfs包修改后的模块:

1. 修改py3Fdfs包使其支持py3,修改upload返回的数据。
2. 原upload 中的upload_by_file函数未写完,在这里调整并补全
3. 删除原upload 中的upload_by_buffer(),(这个函数需要一次性将文件读取到内存，上传文件太吃内存)

该项目将图片转为jpg格式(占用空间小)来保存，并为其生成png格式的缩略图.若是文件测原样保存。

