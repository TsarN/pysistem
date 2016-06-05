import sqlite3
from flask import Flask, g, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_babel import Babel
from contextlib import closing

from pysistem import conf

from concurrent.futures import ThreadPoolExecutor as Pool
pool = Pool(max_workers=1)

app = Flask(__name__)
app.config.from_object(conf)
db = SQLAlchemy(app)

babel = Babel(app)

# Misc functions

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

import pysistem.views

db.create_all()
db.session.commit()
