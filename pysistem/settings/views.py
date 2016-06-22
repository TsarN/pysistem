# -*- coding: utf-8 -*-

"""Server settings views"""

from pysistem import db
from flask import render_template, flash, redirect, url_for, request, Blueprint
from flask_babel import gettext
from pysistem.users.decorators import requires_admin
from pysistem.settings.model import Setting
import re

mod = Blueprint('settings', __name__, url_prefix='/settings')

@mod.route('/', methods=['GET', 'POST'])
@requires_admin
def edit():
    """Edit server settings

    Permissions required:
    Server Administrator
    """

    if request.method == 'POST':
        allow_signup = bool(request.form.get('allow_signup'))
        allow_guest_view = bool(request.form.get('allow_guest_view'))

        username_pattern = request.form.get('username_pattern')
        scoreboard_cache_timeout = int(request.form.get('scoreboard_cache_timeout'))

        if username_pattern:
            is_valid = True
            try:
                re.compile(username_pattern)
            except re.error:
                is_valid = False
            if not is_valid:
                flash('::danger ' + gettext('settings.errors.invalidusernameregex'))
                return redirect(url_for('settings.edit'))

        Setting.set('allow_signup', allow_signup)
        Setting.set('allow_guest_view', allow_guest_view)
        Setting.set('scoreboard_cache_timeout', scoreboard_cache_timeout)
        if username_pattern:
            Setting.set('username_pattern', username_pattern)
        db.session.commit()
        flash(gettext('settings.edit.success'))
        return redirect(url_for('settings.edit'))
    return render_template('settings/edit.html')