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
