# -*- coding: utf-8 -*-

from pysistem import manager
from flask_migrate import MigrateCommand
manager.add_command('db', MigrateCommand)