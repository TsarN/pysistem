# -*- coding: utf-8 -*-

"""User views"""

import re

from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint
from flask_babel import gettext

from pysistem import app, db
from pysistem.users.model import User
from pysistem.submissions.model import Submission
from pysistem.users.decorators import requires_guest, requires_login
from pysistem.groups.model import Group, GroupUserAssociation

mod = Blueprint('users', __name__, url_prefix='/user')

@mod.route('/login', methods=['GET', 'POST'])
@requires_guest
def login():
    """Authorize user"""
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
    """Register new user"""
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
            if re.compile(r"^[A-Za-z0-9_]{3,15}$").match(request.form['username']):
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
    """Log out"""
    session.pop('user_id', None)
    flash(gettext('auth.logout.success'))
    return redirect(url_for('index'))

@mod.route('/<username>')
@mod.route('/')
@requires_login
def profile(username=None):
    """View user's profile"""
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

@mod.route('/<username>/password', methods=['GET', 'POST'])
@mod.route('/password', methods=['GET', 'POST'])
def change_password(username=None):
    """Change user's password"""
    user = g.user
    if username is not None:
        user = User.query.filter( \
                db.func.lower(User.username) == db.func.lower(username)).first()
    if (user is None) or (user.id is None):
        return render_template('errors/404.html'), 404
    if not user.check_permissions():
        return render_template('errors/403.html'), 403

    if request.method == 'POST':
        if user.id == g.user.id:
            old_password = request.form.get('old_password', '')
            old_password_hash = User.signpasswd(user.username, old_password)
            if user.password != old_password_hash:
                flash('::danger ' + gettext('users.changepassword.incorrectoldpassword'))
                return redirect(url_for('users.change_password', username=user.username))
        new_password = request.form.get('new_password', '')
        new_password_confirm = request.form.get('new_password_confirm', '')

        if new_password == new_password_confirm:
            if len(new_password) > 3:
                new_password_hash = User.signpasswd(user.username, new_password)
                user.password = new_password_hash
                db.session.commit()
                flash(gettext('users.changepassword.success'))
            else:
                flash('::danger ' + gettext('users.changepassword.shortpassword'))
        else:
            flash('::danger ' + gettext('users.changepassword.mismatchedpasswords'))
        return redirect(url_for('users.change_password', username=user.username))
    return render_template('users/change_password.html', user=user)

@mod.route('/<username>/edit', methods=['GET', 'POST'])
@mod.route('/edit', methods=['GET', 'POST'])
def edit_profile(username=None):
    """Edit user's profile"""
    user = g.user
    if username is not None:
        user = User.query.filter( \
                db.func.lower(User.username) == db.func.lower(username)).first()
        if user is None:
            return render_template('errors/404.html'), 404
    if not user.check_permissions():
        return render_template('errors/403.html'), 403

    groups = Group.query.all()

    if request.method == 'POST':
        user.first_name = request.form.get('first_name', user.first_name)
        user.last_name = request.form.get('last_name', user.last_name)
        user.email = request.form.get('email', user.email)

        if g.user.is_admin():
            for group in groups:
                radio = request.form.get('group-%d' % group.id, "none")
                checked = (radio == "none")
                role = 'admin' if (radio == 'admin') else 'user'
                assoc = GroupUserAssociation.query.filter(db.and_( \
                    GroupUserAssociation.user_id == user.id, \
                    GroupUserAssociation.group_id == group.id \
                    )).first()
                if assoc and checked:
                    db.session.delete(assoc)
                if not checked:
                    assoc = assoc or GroupUserAssociation()
                    assoc.role = role
                    assoc.user_id = user.id
                    assoc.group_id = group.id
                    db.session.add(assoc)
        db.session.commit()
        flash(gettext('profile.update.success'))
        return redirect(url_for('users.edit_profile', username=user.username))

    group_map = {}
    for group in user.groups:
        group_map[group.group.id] = group.role

    for group in groups:
        group.role_ = group_map.get(group.id)

    del group_map

    return render_template('users/edit_profile.html', user=user, groups=groups)
