from io import BytesIO
from PIL import Image

IMG_TYPE = ('jpg', 'jpeg', 'gif', 'pjpeg', 'bmp', 'png')


def isImg(fileName):
    return '.' in fileName and \
           fileName.rsplit('.', 1)[1].lower() in IMG_TYPE


def getFileSize(f):
    pos = f.tell()
    f.seek(0, 2)
    size = f.tell()
    f.seek(pos)
    return size


def getFileUrl(d):
    if isinstance(d, dict):
        url = "http://{0}/{1}"
        return url.format(d["storage_ip"], d["remote_filename"])
    else:
        return ''


class HandleFile(object):
    def __init__(self, file, appConfig):
        self.MAX_W = appConfig.get("MAX_W", 400)
        self.MAX_H = appConfig.get("MAX_H", 400)
        self.CLIENT_CONF = appConfig.get("CLIENT_CONF", '/etc/fdfs/client.conf')
        if isinstance(file, str):
            self.fileName = file
        else:
            self.fileName = file.filename
        if isImg(self.fileName):
            self.file = Image.open(file).convert('RGBA')
            self.isImg = True
        else:
            self.file = file
            self.isImg = False
        # 缩略图
        self.resizeIm = None

    def createThumbnail(self):
        if self.isImg:
            # 当图片长宽超过规定尺寸，则生成缩略图，否则为None
            width, height = self.file.size
            if width < self.MAX_W and height < self.MAX_H:
                self.resizeIm = self.file
            else:
                if width > height:
                    self.resizeIm = self.file.resize((self.MAX_W, int(height * self.MAX_W / width)))
                else:
                    self.resizeIm = self.file.resize((int(width * self.MAX_H / height), self.MAX_H))

    def convertImgToBytesIO(self):
        if self.isImg:
            # 原图转jpg BytesBytesIO
            if self.file.mode != "RGB":
                self.file = self.file.convert('RGB')
            f1 = BytesIO()
            self.file.save(f1, format="JPEG")
            self.file = f1
            # 缩略图转png BytesIO
            f2 = BytesIO()
            self.resizeIm.save(f2, format="PNG")
            self.resizeIm = f2



