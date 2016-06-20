# -*- coding: utf-8 -*-
import os

# Work directory. Leave as is
DIR = os.path.dirname(os.path.realpath(__file__))

SECRET_KEY = b'\nB\xd3\xa7\x9f\xd6r\x03a&R\x85\x84\xea\x0c\xab\x1eU4\x18O\xad\xda\xed'
DEBUG = False
# Allowed languages
LANGUAGES = {
    'en': 'English',
    'ru': 'Русский'
}
# Database to use
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(DIR, 'sistem.db')
SQLALCHEMY_MIGRATE_REPO = os.path.join(DIR, 'db_repository')
# For debugging
#SQLALCHEMY_ECHO = True

# Auto-created directories. Leave as is
CREATE_DIRS = (
    '/storage/checkers_bin',
    '/storage/submissions_bin'
)

# Extra paths to search compilers in
PATH_EXTRA = []

# How often check submissions
CHECK_THREAD_TIME = 1

# Do check submissions?
LAUNCH_CHECK_THREAD = True