# -*- coding: utf-8 -*-
import os
from flask import Flask, g, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from contextlib import closing
import random
import threading
import atexit
from pysistem import conf
from pysistem.submissions.const import *

app = Flask(__name__)
app.config.from_object(conf)
app.config['CONFIRM_CODE'] = ''.join(random.SystemRandom().choice( \
'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789' \
) for _ in range(12))
db = SQLAlchemy(app)

babel = Babel(app)
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()

CHECK_THREAD_TIME = app.config.get('CHECK_THREAD_TIME', 1)
data_lock = threading.Lock()
check_thread = threading.Thread()
common_data = {}

def interrupt():
    global check_thread
    check_thread.cancel()

def check_thread_wake():
    global common_data
    global check_thread
    with data_lock:
        Session = common_data['Session']
        Submission = common_data['Submission']
        session = Session()
        for sub in session.query(Submission).filter( \
            Submission.status.in_([STATUS_CWAIT, STATUS_WAIT])).all():
            if sub.compile()[0]:
                sub.check(session)
        Session.remove()
    check_thread = threading.Timer(CHECK_THREAD_TIME, check_thread_wake, ())
    check_thread.start()

def check_thread_init():
    global check_thread
    global common_data
    from pysistem.submissions.model import Submission
    common_data['Submission'] = Submission
    Session = db.scoped_session(db.sessionmaker(bind=db.engine))
    common_data['Session'] = Session
    check_thread = threading.Timer(CHECK_THREAD_TIME, check_thread_wake, ())
    check_thread.start()

check_thread_init()
atexit.register(interrupt)

# Misc functions

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

import pysistem.views

try:
    db.create_all()
    db.session.commit()

    for d in conf.CREATE_DIRS:
        if not os.path.exists(conf.DIR + d):
            os.makedirs(conf.DIR + d)

    from pysistem.users.model import User
    if User.query.count() == 0:
        print('---- SIGN UP CONFIRMATION CODE ----')
        print(app.config['CONFIRM_CODE'])
        print('---- SIGN UP CONFIRMATION CODE ----')

    from pysistem.compilers.model import detect_compilers
    detect_compilers()

except: pass
