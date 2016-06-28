# -*- coding: utf-8 -*-
"""Contest management system"""
import os
import random
import sys
import traceback

from flask import Flask, request, url_for
from flask_babel import Babel
from flask_migrate import Migrate
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.contrib.cache import SimpleCache

try:
    from pysistem import conf
except ImportError:
    from pysistem import conf_default

from pysistem.submissions.const import STATUS_CWAIT, STATUS_WAIT

basedir = os.path.dirname(os.path.realpath(__file__))

class PySistemApplication(Flask):
    """Main PySistem WSGI Application"""
    def make_check_thread(self):
        from pysistem.checkthread import CheckThread
        self.check_thread = CheckThread()

    def start_check_thread(self=None, join=False):
        """Start checking thread

        Arguments:
        join -- Do Thread.join()?
        """
        self.make_check_thread()
        self.check_thread.start()
        if join:
            self.check_thread.join()

    def make_dirs(self=None):
        """Create required directories"""
        self = self or app
        for directory in app.config['CREATE_DIRS']:
            if not os.path.exists(os.path.join(self.config['STORAGE'], directory)):
                os.makedirs(os.path.join(self.config['STORAGE'], directory))

    def prerun(self, *args, **kwargs):
        """Make preparations for start"""
        from pysistem.users.model import User
        self.make_dirs()
        if User.query.count() == 0:
            print('---- SIGN UP CONFIRMATION CODE ----')
            print(app.config['CONFIRM_CODE'])
            print('---- SIGN UP CONFIRMATION CODE ----')

        from pysistem.compilers.model import detect_compilers
        detect_compilers()

        if kwargs.get('launch_check_thread', True):
            if app.config.get('LAUNCH_CHECK_THREAD', True):
                self.start_check_thread()

    def run(self, *args, **kwargs):
        """Start Werkzeug WSGI server"""
        self.prerun(*args, **kwargs)
        try:
            Flask.run(self, *args, **kwargs)
            sys.exit(0)
        except SystemExit as exception:
            sys.exit(exception.code)
        except:
            trace = traceback.format_exc()
            print(trace)
            print("Exception occurred, exiting")
            sys.exit(1)

app = PySistemApplication(__name__)
try:
    app.config.from_object(conf)
except NameError:
    app.config.from_object(conf_default)

app.config['CONFIRM_CODE'] = ''.join(random.SystemRandom().choice( \
'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789' \
) for _ in range(12))
app.config['VERSION'] = '0.3-SNAPSHOT'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

babel = Babel(app)
cache = SimpleCache()

# Misc functions

def redirect_url(default='index'):
    """Return previous url"""
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

manager = Manager(app, with_default_commands=False)

from pysistem import views, models

if __name__ == "__main__":
    import pysistem.commands
    manager.run()
