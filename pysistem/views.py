# -*- coding: utf-8 -*-
from werkzeug.routing import BaseConverter
from pysistem import app, babel, db
from flask import render_template, session, g, flash, redirect, url_for, request
import re

from pysistem.users.model import User
from pysistem.contests.model import Contest
from pysistem.submissions.model import Submission
from pysistem.problems.model import Problem
from pysistem.groups.model import Group

from pysistem.conf import LANGUAGES
from flask_babel import gettext
from datetime import time, date, datetime

from pysistem.conf import SETTINGS

@babel.localeselector
def get_locale():
    return session.get('language') or request.accept_languages.best_match(LANGUAGES.keys())

@app.before_request
def before_request():
    if request.path.startswith('/static/'):
        return
    g.is_first_time = (User.query.count() == 0)
    g.now = datetime.now()
    session['language'] = get_locale()
    g.user = User()
    g.now_formatted = datetime.now().strftime("%Y-%m-%d %H:%M")
    g.raw_content = False
    g.SETTINGS = SETTINGS
    if SETTINGS.get('allow_raw_content', False):
        if request.args.get('raw', False) == '1':
            g.raw_content = True

    g.disable_navbar = False
    g.user_groups = {}

    user = None
    if g.user.id:
        user = User.query.get(g.user.id)

    if user:
        if user.is_admin():
            g.user_groups['admin'] = Group.query.all()
        else:
            for group in user.groups:
                if not g.user_groups.get(group.role):
                    g.user_groups[group.role] = []
                g.user_groups[group.role].append(group.group)

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
                    return render_template('guest_view_denied.html', \
                        allow_signup=SETTINGS.get('allow_signup', True))

@app.teardown_request
def teardown_request(*args, **kwargs):
    try:
        del g.is_first_time
        del g.now
        del g.user
        del g.now_formatted
        del g.raw_content
        del g.SETTINGS
        del g.disable_navbar
        del g.user_groups
    except: pass

def pad_zero(x, min_len=2):
    return '0' * (max(0, min_len - len(str(x)))) + str(x)

@app.template_filter('timeonly')
def timeonly_filter(seconds, enable_seconds=True, cycle=False):
    hours = int(seconds // 3600)
    if cycle:
        hours %= 24
    minutes = int(seconds % 3600 // 60)
    if enable_seconds:
        seconds = int(seconds % 60)
        return pad_zero(hours) + ':' + pad_zero(minutes) + ':' + pad_zero(seconds)
    else:
        return pad_zero(hours) + ':' + pad_zero(minutes)

@app.template_filter('shortstr')
def shortstr_filter(s, length=5):
    if len(s) > length:
        return s[:length] + '...'
    else:
        return s

@app.template_filter('dtp')
def dtp_filter(date):
    return date.strftime("%Y-%m-%d %H:%M")

@app.template_filter('naturaldate')
def naturaldate_filter(date):
    try:
        import humanize
        if session.get('language') != "en":
            humanize.i18n.activate(session.get('language'))
        else:
            humanize.i18n.deactivate()
        date_str = humanize.naturaldate(date)
        today = datetime.combine(date.today(), time(0))
        seconds = int((date-today).total_seconds())
        return date_str + ' ' + timeonly_filter(seconds, enable_seconds=False, cycle=True)
    except: pass
    return dtp_filter(date)

@app.template_filter('duration')
def duration_filter(delta):
    try:
        import humanize
        if session.get('language') != "en":
            humanize.i18n.activate(session.get('language'))
        else:
            humanize.i18n.deactivate()
        return humanize.naturaldelta(delta)
    except: pass
    return timeonly_filter(delta.total_seconds())

@app.template_filter('ids')
def ids_filter(obj):
    return [x.id for x in obj]

@app.template_filter('limittext')
def limittext_filter(text, x=25, y=10, compacted=None):
    splitted = text.split('\n')
    cols = max(map(lambda x: len(x), splitted))
    rows = len(splitted)
    if (cols > x) or (rows > y):
        return compacted
    else:
        return text

@app.template_filter('naturaltime')
def naturaltime_filter(time=False):
    now = datetime.now()
    try:
        import humanize
        if session.get('language') != "en":
            humanize.i18n.activate(session.get('language'))
        else:
            humanize.i18n.deactivate()
        return humanize.naturaltime(time)
    except: pass
    # http://stackoverflow.com/a/1551394

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

class StrListConverter(BaseConverter):
    regex = r'[^,]+(?:,[^,]+)*,?'

    def to_python(self, value):
        return value.split(',')

    def to_url(self, value):
        return ','.join(value)

app.url_map.converters['str_list'] = StrListConverter

class IntListConverter(BaseConverter):
    regex = r'\d+(?:,\d+)*,?'

    def to_python(self, value):
        return [int(x) for x in value.split(',')]

    def to_url(self, value):
        return ','.join([str(x) for x in value])

app.url_map.converters['int_list'] = IntListConverter


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

from pysistem.test_pairs.views import mod as test_pairs_module
app.register_blueprint(test_pairs_module)

from pysistem.groups.views import mod as groups_module
app.register_blueprint(groups_module)

from pysistem.lessons.views import mod as lessons_module
app.register_blueprint(lessons_module)