# -*- coding: utf-8 -*-
from pysistem import app, babel, db
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint
import re
from pysistem.users.model import User
from pysistem.submissions.model import Submission
from pysistem.users.decorators import requires_guest, requires_login
from flask_babel import gettext

mod = Blueprint('users', __name__, url_prefix='/user')

@mod.route('/login', methods=['GET', 'POST'])
@requires_guest
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        status, result = User.auth(username, password)
        if status:
            flash(gettext('auth.login.success'))
            return redirect(url_for('index'))
        else:
            error = gettext(result)
    return render_template('users/login.html', error=error)

@mod.route('/signup', methods=['GET', 'POST'])
@requires_guest
def signup():
    if not g.SETTINGS.get('allow_signup', True) and not g.is_first_time:
        flash('::danger ' + gettext('auth.signup.forbidden'))
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        password_confirm = request.form.get('passwordConfirm', '')
        confirm_code = request.form.get('confirmCode', '').strip(' \t\n\r')
        if g.is_first_time and (confirm_code != app.config['CONFIRM_CODE']):
            error = gettext('auth.signup.admin.invalidcode')
        else:
            if re.compile(g.SETTINGS.get('username_pattern', '.*')).match(request.form['username']):
                if not User.exists(username):
                    if password == password_confirm:
                        if len(password) > 3:
                            user = User(username, password)
                            if g.is_first_time:
                                user.role = 'admin'
                            db.session.add(user)
                            db.session.commit()
                            User.auth(username, password)
                            flash(gettext('auth.signup.success'))
                            return redirect(url_for('index'))
                        else:
                            error = gettext('auth.signup.shortpassword')
                    else:
                        error = gettext('auth.signup.mismatchedpasswords')
                else:
                    error = gettext('auth.signup.exists')
            else:
                error = gettext('auth.signup.invalidusername')
    return render_template('users/signup.html', error=error)

@mod.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('user_id', None)
    flash(gettext('auth.logout.success'))
    return redirect(url_for('index'))

@mod.route('/<username>')
@mod.route('/')
def profile(username=None):
    user = g.user
    if username is not None:
        user = User.query.filter( \
                db.func.lower(User.username) == db.func.lower(username)).first()
        if user is None:
            return render_template('errors/404.html'), 404
    submissions = Submission.query.filter(
        Submission.user_id == user.id).all()
    rendered_subs = render_template('submissions/list.html',
        submissions=submissions, show_problem=True)
    return render_template('users/profile.html', user=user, rendered_subs=rendered_subs)

@mod.route('/<username>/edit', methods=['GET', 'POST'])
@mod.route('/edit', methods=['GET', 'POST'])
def edit_profile(username):
    user = g.user
    if username is not None:
        user = User.query.filter( \
                db.func.lower(User.username) == db.func.lower(username)).first()
        if user is None:
            return render_template('errors/404.html'), 404
    if not user.check_permissions():
        return render_template(url_for('errors/403.html')), 403
    if request.method == 'POST':
        if request.form.get('update_info', None) is not None:
            user.first_name = request.form.get('first_name', user.first_name)
            user.last_name = request.form.get('last_name', user.last_name)
            user.email = request.form.get('email', user.email)
            if g.user.is_admin(user=user):
                username = request.form.get('username', user.username)
                if re.compile(g.SETTINGS.get('username_pattern', '.*')).match(username):
                    if not User.exists(username):
                        user.username = username
            db.session.commit()
            flash(gettext('profile.update.success'))
            return redirect(url_for('users.profile', id=user.id))
    return render_template('users/edit_profile.html', user=user)