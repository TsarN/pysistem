# -*- coding: utf-8 -*-

"""Submissions decorators"""

from functools import wraps

from flask import render_template

from pysistem.submissions.model import Submission

def yield_submission(field='submission_id', yield_field='submission'):
    """Decorator
    Get submission identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If submission does not exist return 404 Not Found error
    """
    def decorator(func):
        """Decorator of yield_submission"""
        @wraps(func)
        def decorated_function(*args, **kwargs):
            """Decorated of yield_submission"""
            submission = Submission.query.get(int(kwargs.get(field)))
            if submission is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = submission
            return func(*args, **kwargs)
        return decorated_function
    return decorator
