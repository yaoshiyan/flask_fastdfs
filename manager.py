import logging

from flask_script import Manager

from app import create_app
app = create_app('default')
manager = Manager(app)

# 将flask日志与gunicorn日志合并
gunicorn_logger = logging.getLogger("gunicorn.error")
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

if __name__ == '__main__':
    manager.run()
