from flask import Flask

from config import config


def create_app(config_name):
	app = Flask(__name__)
	app_config = config[config_name]
	app.config.from_object(app_config)

	from .uploadFile import uploadFile as uploadFile_blueprint
	app.register_blueprint(uploadFile_blueprint)

	return app
