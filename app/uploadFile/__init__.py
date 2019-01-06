from flask import Blueprint

uploadFile = Blueprint('uploadFile', __name__)
from . import view
