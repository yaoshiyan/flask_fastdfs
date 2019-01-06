import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
	SECRET_KEY = "SJCH429jwnEbfzpIil11@#w1fJ[f]3a"
	# 处理图片
	MAX_W = 400
	MAX_H = 400
	# fastdfs 客户端配置路径
	CLIENT_CONF = '/etc/fdfs/client.conf'


class DevelopementConfig(Config):
	DEBUG = True


class ProductionConfig(Config):
	DEBUG = False


config = {
	'default': DevelopementConfig,
	'development': DevelopementConfig,
	'production': ProductionConfig
}
