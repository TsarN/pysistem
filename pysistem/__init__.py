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
    from pysistem.conf import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO
except: pass
from pysistem.submissions.const import *
import sys
import imp

from migrate.versioning import api

basedir = os.path.dirname(os.path.realpath(__file__))

class PySistemApplication(Flask):
    def db_create(self=None):
        print("Creating database")
        db.create_all()
        try:
            if not os.path.exists(SQLALCHEMY_MIGRATE_REPO):
                api.create(SQLALCHEMY_MIGRATE_REPO,
                    'pysistem')

                api.version_control(
                    SQLALCHEMY_DATABASE_URI,
                    SQLALCHEMY_MIGRATE_REPO)
            else:
                api.version_control(
                    SQLALCHEMY_DATABASE_URI,
                    SQLALCHEMY_MIGRATE_REPO,
                    api.version(SQLALCHEMY_MIGRATE_REPO))
        except: pass
        print("Done")

    def db_migrate(self=None, name=None):
        version = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
        if type(name) is str:
            name = name.lower()
            name = name.replace(' ', '_')
        name = ('_' + name) if type(name) is str else ''
        migration = SQLALCHEMY_MIGRATE_REPO + ('/versions/%03d%s_migration.py' % (version + 1, name))
        tmp_module = imp.new_module('old_model')
        old_model = api.create_model(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)

        exec(old_model, tmp_module.__dict__)
        script = api.make_update_script_for_model(SQLALCHEMY_DATABASE_URI,
            SQLALCHEMY_MIGRATE_REPO, tmp_module.meta, db.metadata)
        open(migration, "wt").write(script)
        api.upgrade(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
        version = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
        print("New migration saved as", migration)
        print("Current database version:", version)

    def db_upgrade(self=None):
        api.upgrade(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
        version = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
        print("Current database version:", version)

    def db_downgrade(self=None, revision=None):
        version = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
        if not revision:
            revision = version - 1
        api.downgrade(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO, revision)
        version = api.db_version(SQLALCHEMY_DATABASE_URI, SQLALCHEMY_MIGRATE_REPO)
        print("Current database version:", version)

    def config_default(self=None):
        from shutil import copyfile
        copyfile(os.path.join(basedir, 'conf_default.py'), os.path.join(basedir, 'conf.py'))
        print("Default configuration copied")

    def config_gensecret(self=None):
        with open(os.path.join(basedir, 'conf.py'), "r") as f:
            config = f.read()
        import re
        regex = re.compile('^[ \t\r\n]*SECRET_KEY')
        replacement = 'SECRET_KEY = ' + str(os.urandom(24))
        new_config = '\n'.join([replacement if regex.match(x) else x for x in config.split('\n')])

        with open(os.path.join(basedir, 'conf.py'), "w") as f:
            f.write(new_config)

        print("Done")

    def tests_run(self=None):
        from pysistem.tests import TestCase
        import unittest
        suite = unittest.TestLoader().loadTestsFromTestCase(TestCase)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        sys.exit(len(result.failures))

    def start_check_thread(self=None):
        check_thread_init()
        atexit.register(check_thread_interrupt)

    def console_interface(self=None):
        actions = {
            "wsgi:start": "Start WSGI server using Werkzeug",
            "checker:start": "Start checker thread alone",
            "db:create": "Create database",
            "db:migrate": """
                Create database migration.
                Accepts string as database migration name
            """,
            "db:upgrade": "Upgrade database to latest version",
            "db:downgrade": """
                Downgrade database.
                Accepts integer as database revision to downgrade to
            """,
            "config:default": "Create default configuration",
            "config:gensecret": "Generate new secret key and save it into conf.py",
            "tests:run": "Run tests"
        }

        action = sys.argv[1] if len(sys.argv) > 1 else ''
        
        if action not in actions.keys():
            print("Usage: <action> [parameters]")
            print()
            print("Actions available:")
            max_name_len = max([len(x) for x in actions.keys()])
            for action in sorted(actions.keys()):
                left_column = "  " + action.ljust(max_name_len) + "  "
                description = actions[action].split("\n")
                description = [x for x in description if x.strip()]
                print(left_column, description[0].strip(), sep="")
                for desc in description[1:]:
                    print(" " * len(left_column), desc.strip(), sep="")
            sys.exit(1)

        if action == "wsgi:start":
            self.run()
        elif action == "checker:start":
            self.start_check_thread()
            check_thread.join()
        elif action == "db:create":
            self.db_create()
        elif action == "db:migrate":
            name = sys.argv[2] if len(sys.argv) > 2 else None
            self.db_migrate(name)
        elif action == "db:upgrade":
            self.db_upgrade()
        elif action == "db:downgrade":
            version = sys.argv[2] if len(sys.argv) > 2 else None
            try:
                version = int(version)
            except:
                print("Database revision must be an int")
                sys.exit(1)
            self.db_downgrade(version)
        elif action == "config:default":
            self.config_default()
        elif action == "config:gensecret":
            self.config_gensecret()
        elif action == "tests:run":
            self.tests_run()
        else:
            print("Not implemented")
            sys.exit(1)

    def make_dirs(self=None):
        for d in app.config['CREATE_DIRS']:
            if not os.path.exists(os.path.join(app.config['STORAGE'], d)):
                os.makedirs(os.path.join(app.config['STORAGE'], d))

    def run(self):
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

        return Flask.run(self)

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

from pysistem import views, models

if __name__ == "__main__":
    app.console_interface()