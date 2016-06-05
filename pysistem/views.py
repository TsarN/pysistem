from pysistem import app, babel, db
from flask import render_template, session, g, flash, redirect, url_for, request
import re

from pysistem.users.model import User
from pysistem.contests.model import Contest
from pysistem.submissions.model import Submission

from pysistem.conf import LANGUAGES
from flask_babel import gettext
from datetime import datetime

from pysistem.conf import SETTINGS

@babel.localeselector
def get_locale():
    return session.get('language') or request.accept_languages.best_match(LANGUAGES.keys())

@app.before_request
def before_request():
    g.is_first_time = (User.query.count() == 0)
    g.user = User()
    g.now_formatted = datetime.now().strftime("%Y-%m-%d %H:%M")
    g.now = datetime.now()
    g.raw_content = False
    g.SETTINGS = SETTINGS
    if SETTINGS.get('allow_raw_content', False):
        if request.args.get('raw', False) == '1':
            g.raw_content = True

    g.disable_navbar = False

    if not SETTINGS.get('allow_guest_view', True) or g.is_first_time:
        if (g.user.id is None) and \
        (not request.path.startswith('/static/')) and \
        (not request.path.startswith('/locale/set/')):
            g.disable_navbar = True
            if g.is_first_time:
                if not request.path.startswith(url_for('users.signup')):
                    return redirect(url_for('users.signup'))
            else:
                allowed_urls = [url_for('users.login')]
                if SETTINGS.get('allow_signup', True):
                    allowed_urls.append(url_for('users.signup'))
                if request.path not in allowed_urls:
                    return render_template('guest_view_denied.html', allow_signup=SETTINGS.get('allow_signup', True))

def pad_zero(x, min_len=2):
    return '0' * (max(0, min_len - len(str(x)))) + str(x)

@app.template_filter('timeonly')
def timeonly_filter(seconds):
    hours = int(seconds // 3600)
    minutes = int(seconds % 3600 // 60)
    seconds = int(seconds % 60)
    return pad_zero(hours) + ':' + pad_zero(minutes) + ':' + pad_zero(seconds)

@app.template_filter('naturaltime')
def naturaltime_filter(time=False):

    # http://stackoverflow.com/a/1551394

    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time,datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = int(diff.seconds)
    day_diff = int(diff.days)

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return gettext('naturaltime.justnow')
        if second_diff < 60:
            return str(second_diff) + " " + gettext('naturaltime.secondsago')
        if second_diff < 120:
            return gettext('naturaltime.minuteago')
        if second_diff < 3600:
            return str(second_diff // 60) + " " + gettext('naturaltime.minutesago')
        if second_diff < 7200:
            return gettext('naturaltime.hourago')
        if second_diff < 86400:
            return str(second_diff // 3600) + " " + gettext('naturaltime.hoursago')
    if day_diff == 1:
        return gettext('naturaltime.yesterday')
    if day_diff < 7:
        return str(day_diff) + " " + gettext('naturaltime.daysago')
    if day_diff < 14:
        return gettext('naturaltime.weekago')
    if day_diff < 31:
        return str(day_diff // 7) + " " + gettext('naturaltime.weeksago')
    if day_diff < 60:
        return gettext('naturaltime.monthago')
    if day_diff < 365:
        return str(day_diff // 30) + " " + gettext('naturaltime.monthsago')
    return str(day_diff // 365) + " " + gettext('naturaltime.yearsago')

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

from pysistem.submissions.views import mod as submissions_module
app.register_blueprint(submissions_module)