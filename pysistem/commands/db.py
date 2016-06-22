# -*- coding: utf-8 -*-
"""Database-related commands provided by Flask-Migrate"""

from flask_migrate import MigrateCommand
from pysistem import manager
manager.add_command('db', MigrateCommand)
