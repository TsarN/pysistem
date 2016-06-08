# -*- coding: utf-8 -*-
import os
from flask import Flask, g, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from contextlib import closing
import random

from pysistem import conf

from concurrent.futures import ThreadPoolExecutor as Pool
pool = Pool(max_workers=1)

app = Flask(__name__)
app.config.from_object(conf)
app.config['CONFIRM_CODE'] = ''.join(random.SystemRandom().choice( \
'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789' \
) for _ in range(12))
db = SQLAlchemy(app)

babel = Babel(app)
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()

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

    from pysistem.submissions.model import Submission
    from pysistem.submissions.const import *
    for sub in Submission.query.filter( \
        Submission.status.in_([STATUS_CWAIT, STATUS_COMPILING, \
            STATUS_WAIT, STATUS_CHECKING])).all():
        sub.async_check()
        print("Restarting check for", sub)
except: pass
