# -*- coding: utf-8 -*-
import os

SECRET_KEY = b'\nB\xd3\xa7\x9f\xd6r\x03a&R\x85\x84\xea\x0c\xab\x1eU4\x18O\xad\xda\xed'
# Set to False in production enviroments
DEBUG = True
# Allowed languages
LANGUAGES = {
    'en': 'English',
    'ru': 'Русский'
}
# Database to use
SQLALCHEMY_DATABASE_URI = "sqlite:///sistem.db"
SQLALCHEMY_TRACK_MODIFICATIONS = True
# For debugging
#SQLALCHEMY_ECHO = True

# Work directory. Leave as is
DIR = os.path.dirname(os.path.realpath(__file__))

# Server settings
SETTINGS = {
    "allow_signup": True,
    "allow_guest_view": True,
    "allow_raw_content": False,
    "username_pattern": "^[A-Za-z0-9_]{3,15}$",
    "scoreboard_cache_timeout": 60
}

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