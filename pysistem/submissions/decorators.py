# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext
from pysistem.submissions.model import Submission

def yield_submission(field='id', yield_field='submission'):
    """Decorator
    Get submission identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If submission does not exist return 404 Not Found error
    """
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