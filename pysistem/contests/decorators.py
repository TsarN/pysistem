# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext
from pysistem.contests.model import Contest

def yield_contest(field='contest_id', yield_field='contest'):
    """Decorator
    Get contest identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If contest does not exist return 404 Not Found error
    """
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            contest = Contest.query.get(int(kwargs.get(field)))
            if contest is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = contest
            return func(*args, **kwargs)
        return decorated_function
    return decorator