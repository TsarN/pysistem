import os
SECRET_KEY = b'\nB\xd3\xa7\x9f\xd6r\x03a&R\x85\x84\xea\x0c\xab\x1eU4\x18O\xad\xda\xed'
DEBUG = True
USERNAME_PATTERN = "^[A-Za-z0-9_]{3,15}$"
LANGUAGES = {
    'en': 'English',
    'ru': 'Русский'
}
SQLALCHEMY_DATABASE_URI = "sqlite:///sistem.db"
SQLALCHEMY_TRACK_MODIFICATIONS = True
#SQLALCHEMY_ECHO = True
DIR = os.path.dirname(os.path.realpath(__file__))
PROCESSES=4