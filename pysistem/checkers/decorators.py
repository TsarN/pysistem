# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext
from pysistem.checkers.model import Checker

def yield_checker(field='id', yield_field='checker'):
    # Yield checker identified by 'field' to 'yield_field'
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            checker = Checker.query.get(int(kwargs.get(field)))
            if checker is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = checker
            return f(*args, **kwargs)
        return decorated_function
    return decorator