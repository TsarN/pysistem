# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext
from pysistem.contests.model import Contest

def yield_contest(field='id', yield_field='contest'):
    # Yield contest identified by 'field' to 'yield_field'
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            contest = Contest.query.get(int(kwargs.get(field)))
            if contest is None:
                return render_template('errors/404.html')
            kwargs[yield_field] = contest
            return f(*args, **kwargs)
        return decorated_function
    return decorator