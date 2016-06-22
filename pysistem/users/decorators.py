# -*- coding: utf-8 -*-

"""User and Auth decorators"""

from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext

def requires_login(func):
    """Decorator
    Display page if user is authorized, else redirect to Log In page
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        """Decorated of requires_login"""
        if g.user.is_guest():
            flash('::warning ' + gettext('error.permission.authrequired'))
            return redirect(url_for('users.login'))
        return func(*args, **kwargs)
    return decorated_function

def requires_guest(func):
    """Decorator
    Display page if user is unauthorized, else return 403 Forbidden error
    """
    @wraps(func)
    def decorated_function(*args, **kwargs):
        """Decorated of requires_guest"""
        if not g.user.is_guest():
            return render_template('errors/403.html'), 403
        return func(*args, **kwargs)
    return decorated_function

def requires_admin(*args_, **kwargs_):
    """Decorator
    Display page if user has correct rights, else return 403 Forbidden error
    """
    def decorator(func):
        """Decorator of requires_admin"""
        @wraps(func)
        def decorated_function(*args, **kwargs):
            """Decorated of requires_admin"""
            new_kwargs = dict(kwargs_)
            for kwarg in kwargs_:
                if type(kwargs_[kwarg]) is str:
                    new_kwargs[kwarg] = kwargs.get(kwargs_[kwarg])
            if not g.user.is_admin(**new_kwargs):
                return render_template('errors/403.html'), 403
            return func(*args, **kwargs)
        return decorated_function
    if (len(args_) > 0) and callable(args_[0]):
        return decorator(args_[0])
    return decorator