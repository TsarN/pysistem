from pysistem import app, babel, db
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint
import re
from pysistem.users.model import User
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

@mod.route('/profile', methods=['GET', 'POST'])
@requires_login
def profile():
    error = None
    if request.method == 'POST':
        if request.form.get('update_info', None) is not None:
            g.user.first_name = request.form.get('first_name', g.user.first_name)
            g.user.last_name = request.form.get('last_name', g.user.last_name)
            g.user.email = request.form.get('email', g.user.email)
            db.session.merge(g.user)
            db.session.commit()
            flash(gettext('profile.update.success'))
            return redirect(url_for('users.profile'))
    return render_template('users/profile.html', error=error)
