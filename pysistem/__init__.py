import sqlite3
from flask import Flask, g, request
from flask_sqlalchemy import SQLAlchemy
from flask_celery import Celery
from flask_babel import Babel
from contextlib import closing

from pysistem import conf

app = Flask(__name__)
app.config.from_object(conf)
db = SQLAlchemy(app)

babel = Babel(app)

celery = Celery(app)

class SqlAlchemyTask(celery.Task):
    abstract = True

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        db.session.remove()

# Misc functions

def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

import pysistem.views

db.create_all()
db.session.commit()