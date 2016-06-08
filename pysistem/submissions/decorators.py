# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext
from pysistem.submissions.model import Submission

def yield_submission(field='id', yield_field='submission'):
    # Yield submission identified by 'field' to 'yield_field'
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            submission = Submission.query.get(int(kwargs.get(field)))
            if submission is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = submission
            return f(*args, **kwargs)
        return decorated_function
    return decorator