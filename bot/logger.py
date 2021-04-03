import logging
from logging.handlers import RotatingFileHandler
import os
import sys

from bot import vars


def initialize_logger(config):
    level = logging.getLevelName(config['level'])
    formatter = logging.Formatter(config['format'])
    handlers = []
    if config['mode'] >= 2:
        if os.path.isdir(os.path.join(*os.path.split(config['file_name'])[0:-1])):
            file = config['file_name']
        else:
            file = os.path.join(vars.directory, config['file_name'])
        rotating_file_handler = RotatingFileHandler(filename=file, mode='a', maxBytes=config['max_file_size'] * 1024, backupCount=config['backup_count'], encoding='UTF-8')
        rotating_file_handler.setFormatter(formatter)
        rotating_file_handler.setLevel(level)
        handlers.append(rotating_file_handler)
    if config['mode'] == 1 or config['mode'] == 3:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(level)
        handlers.append(stream_handler)
    logging.basicConfig(level=level, format=config['format'], handlers=handlers)
