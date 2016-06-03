from pysistem import app, babel, db
from flask import render_template, session, g, flash, redirect, url_for, request
import re

from pysistem.users.model import User
from pysistem.contests.model import Contest
from pysistem.submissions.model import Submission

from pysistem.conf import LANGUAGES
from flask_babel import gettext
from datetime import datetime

@babel.localeselector
def get_locale():
    return session.get('language') or request.accept_languages.best_match(LANGUAGES.keys())

@app.before_request
def before_request():
    g.user = User()
    g.now_formatted = datetime.now().strftime("%Y-%m-%d %H:%M")
    g.now = datetime.now()
    g.raw_content = False
    if request.args.get('raw', False) == '1':
        g.raw_content = True

def pad_zero(x, min_len=2):
    return '0' * (max(0, min_len - len(str(x)))) + str(x)

@app.template_filter('timeonly')
def timeonly_filter(seconds):
    hours = int(seconds // 3600)
    minutes = int(seconds % 3600 // 60)
    seconds = int(seconds % 60)
    return pad_zero(hours) + ':' + pad_zero(minutes) + ':' + pad_zero(seconds)

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def err_notfound(e):
    return render_template('errors/404.html'), 404

# Register modules
from pysistem.users.views import mod as users_module
app.register_blueprint(users_module)

from pysistem.locale.views import mod as locale_module
app.register_blueprint(locale_module)

from pysistem.problems.views import mod as problems_module
app.register_blueprint(problems_module)

from pysistem.contests.views import mod as contests_module
app.register_blueprint(contests_module)