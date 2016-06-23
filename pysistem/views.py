# -*- coding: utf-8 -*-

"""PySistem views loader"""

from datetime import time, datetime
from werkzeug.routing import BaseConverter
from flask import render_template, session, g, redirect, url_for, request

from pysistem.users.model import User
from pysistem.groups.model import Group
try:
    from pysistem.conf import LANGUAGES
except ImportError: # pragma: no cover
    from pysistem.conf_default import LANGUAGES
    
from pysistem import app, babel
from pysistem.settings.model import Setting as SETTINGS

@babel.localeselector
def get_locale():
    """Get current locale. Required for proper Babel operation"""
    return session.get('language') or request.accept_languages.best_match(LANGUAGES.keys())

@app.before_request
def before_request():
    """Process before request"""
    if request.path.startswith('/static/'):
        return
    g.is_first_time = (User.query.count() == 0)
    g.now = datetime.now()
    session['language'] = get_locale()
    g.locale = session['language']
    g.user = User.query.get(session.get('user_id', -1)) or User()
    g.now_formatted = datetime.now().strftime("%Y-%m-%d %H:%M")
    g.raw_content = False
    g.SETTINGS = SETTINGS

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
    """Delete context globals on teardown"""
    try:
        del g.is_first_time
        del g.now
        del g.user
        del g.now_formatted
        del g.raw_content
        del g.SETTINGS
        del g.disable_navbar
        del g.user_groups
        del g.locale
    except AttributeError:
        pass

def pad_zero(number, min_len=2):
    """Pad number with zeroes to at least min_len"""
    return '0' * (max(0, min_len - len(str(number)))) + str(number)

@app.template_filter('timeonly')
def timeonly_filter(seconds, enable_seconds=True, cycle=False):
    """Display time in seconds in format hh+:mm:ss"""
    hours = int(seconds // 3600)
    if cycle:
        hours %= 24
    minutes = int(seconds % 3600 // 60)
    if enable_seconds:
        seconds = int(seconds % 60)
        return pad_zero(hours) + ':' + pad_zero(minutes) + ':' + pad_zero(seconds)
    else:
        return pad_zero(hours) + ':' + pad_zero(minutes)

@app.template_filter('dtp')
def dtp_filter(date):
    """Format date for Bootstrap-Datetimepicker"""
    return date.strftime("%Y-%m-%d %H:%M")

@app.template_filter('naturaldate')
def naturaldate_filter(date):
    """Try to use Humanize to show natural date"""
    try:
        import humanize
        if session.get('language') != "en": # pragma: no cover
            humanize.i18n.activate(session.get('language'))
        else:
            humanize.i18n.deactivate()
        date_str = humanize.naturaldate(date)
        today = datetime.combine(date.today(), time(0))
        seconds = int((date-today).total_seconds())
        return date_str + ' ' + timeonly_filter(seconds, enable_seconds=False, cycle=True)
    except ImportError: # pragma: no cover
        return dtp_filter(date)

@app.template_filter('ids')
def ids_filter(obj):
    """Convert list of SQLAlchemy objects to list of their ids"""
    return [x.id for x in obj]

@app.template_filter('limittext')
def limittext_filter(text, width=25, height=10, compacted=None):
    splitted = text.split('\n')
    cols = max([len(line) for line in splitted])
    rows = len(splitted)
    if (cols > width) or (rows > height):
        return compacted
    else:
        return text

@app.template_filter('naturaltime')
def naturaltime_filter(date=False):
    """Try to use humanize to format date naturally"""
    now = datetime.now()
    try:
        import humanize
        if session.get('language') != "en": # pragma: no cover
            humanize.i18n.activate(session.get('language'))
        else:
            humanize.i18n.deactivate()
        return humanize.naturaltime(date)
    except ImportError: # pragma: no cover
        return dtp_filter(date)

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.errorhandler(404)
def err_notfound(exception):
    """HTTP 404 Not Found handler"""
    return render_template('errors/404.html'), 404

class StrListConverter(BaseConverter):
    """Converter that accepts comma-separated list of strings"""
    regex = r'[^,]+(?:,[^,]+)*,?'

    def to_python(self, value):
        return value.split(',')

    def to_url(self, value): # pragma: no cover
        return ','.join(value)

app.url_map.converters['str_list'] = StrListConverter

class IntListConverter(BaseConverter):
    """Converter that accepts comma-separated list of ints"""
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

from pysistem.settings.views import mod as settings_module
app.register_blueprint(settings_module)
