# -*- coding: utf-8 -*-

"""Checker decorators"""

from functools import wraps

from flask import render_template

from pysistem.checkers.model import Checker

def yield_checker(field='checker_id', yield_field='checker'):
    """Decorator
    Get checker identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If checker does not exist return 404 Not Found error
    """
    def decorator(func):
        """Decorator of yield_checker"""
        @wraps(func)
        def decorated_function(*args, **kwargs):
            """Decorated of yield_checker"""
            checker = Checker.query.get(int(kwargs.get(field)))
            if checker is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = checker
            return func(*args, **kwargs)
        return decorated_function
    return decorator
