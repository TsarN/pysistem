# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext

def requires_login(f):
    # Deny unauthorized
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user.is_guest():
            flash('::warning ' + gettext('error.permission.authrequired'))
            return redirect(url_for('users.login'))
        return f(*args, **kwargs)
    return decorated_function

def requires_guest(f):
    # Deny authorized
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user.is_guest():
            return render_template('errors/403.html'), 403
        return f(*args, **kwargs)
    return decorated_function

def requires_admin(*args_, **kwargs_):
    # Deny unprivileged
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            for kw in kwargs_:
                if type(kwargs_[kw]) is str:
                    kwargs_[kw] = kwargs[kw]
            if not g.user.is_admin(**kwargs_):
                return render_template('errors/403.html'), 403
            return f(*args, **kwargs)
        return decorated_function
    if (len(args_) > 0) and callable(args_[0]):
        return decorator(args_[0])
    return decorator