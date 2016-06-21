# -*- coding: utf-8 -*-
import os
from flask import Flask, g, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
import random
import threading
import atexit
try:
    from pysistem import conf
    from pysistem.conf import SQLALCHEMY_DATABASE_URI
except: pass
from pysistem.submissions.const import *
import sys
import imp

from migrate.versioning import api
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

import traceback

basedir = os.path.dirname(os.path.realpath(__file__))

class PySistemApplication(Flask):
    def start_check_thread(self=None, join=False):
        check_thread_init()
        atexit.register(check_thread_interrupt)
        print("Checker thread started")
        if join:
            check_thread.join()

    def make_dirs(self=None):
        for d in app.config['CREATE_DIRS']:
            if not os.path.exists(os.path.join(app.config['STORAGE'], d)):
                os.makedirs(os.path.join(app.config['STORAGE'], d))

    def run(self, *args, **kwargs):
        self.make_dirs()
        
        from pysistem.users.model import User
        if User.query.count() == 0:
            print('---- SIGN UP CONFIRMATION CODE ----')
            print(app.config['CONFIRM_CODE'])
            print('---- SIGN UP CONFIRMATION CODE ----')

            from pysistem.compilers.model import detect_compilers
            detect_compilers()
            
        if app.config.get('LAUNCH_CHECK_THREAD', True):
            self.start_check_thread()

        try:
            Flask.run(self, *args, **kwargs)
            check_thread_interrupt()
            sys.exit(0)
        except SystemExit as e:
            check_thread_interrupt()
            sys.exit(e.code)
        except:
            tb = traceback.format_exc()
            check_thread_interrupt()
            print(tb)
            print("Exception occurred, exiting")
            sys.exit(1)

app = PySistemApplication(__name__)
try:
    app.config.from_object(conf)
except:
    from pysistem import conf_default
    app.config.from_object(conf_default)
app.config['CONFIRM_CODE'] = ''.join(random.SystemRandom().choice( \
'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789' \
) for _ in range(12))
app.config['VERSION'] = '0.2-SNAPSHOT'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

babel = Babel(app)
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()

CHECK_THREAD_TIME = app.config.get('CHECK_THREAD_TIME', 1)
data_lock = threading.Lock()
check_thread = threading.Thread()
common_data = {}

def check_thread_interrupt():
    global check_thread
    check_thread.cancel()

def check_thread_wake():
    """Check submissions"""
    global common_data
    global check_thread
    with data_lock:
        Session = common_data['Session']
        Submission = common_data['Submission']
        Compiler = common_data['Compiler']
        SubmissionLog = common_data['SubmissionLog']
        session = Session()
        for sub in session.query(Submission).filter( \
            Submission.status.in_([STATUS_CWAIT, STATUS_WAIT])):

            compiler = session.query(Compiler).filter(Compiler.id == sub.compiler_id).first()
            if compiler and compiler.is_available():
                for log in session.query(SubmissionLog) \
                    .filter(SubmissionLog.submission_id == sub.id):
                    session.add(log)
                    session.delete(log)
                if sub.compile()[0]:
                    sub.check(session)
                session.commit()
        Session.remove()
    check_thread = threading.Timer(CHECK_THREAD_TIME, check_thread_wake, ())
    check_thread.start()

def check_thread_init():
    global check_thread
    global common_data
    from pysistem.submissions.model import Submission
    from pysistem.submissions.model import SubmissionLog
    from pysistem.compilers.model import Compiler
    common_data['Submission'] = Submission
    common_data['SubmissionLog'] = SubmissionLog
    common_data['Compiler'] = Compiler
    Session = db.scoped_session(db.sessionmaker(bind=db.engine))
    common_data['Session'] = Session
    check_thread = threading.Timer(CHECK_THREAD_TIME, check_thread_wake, ())
    check_thread.start()

# Misc functions

def redirect_url(default='index'):
    """Return previous url"""
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

manager = Manager(app, with_default_commands=False)

from pysistem import views, models

if __name__ == "__main__":
    from pysistem.commands import *
    manager.run()