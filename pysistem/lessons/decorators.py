# -*- coding: utf-8 -*-

"""Lesson decorators"""

from functools import wraps

from flask import render_template

from pysistem.lessons.model import Lesson

def yield_lesson(field='lesson_id', yield_field='lesson'):
    """Decorator
    Get lesson identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If lesson does not exist return 404 Not Found error
    """
    def decorator(func):
        """Decorator of yield_lesson"""
        @wraps(func)
        def decorated_function(*args, **kwargs):
            """Decorated of yield_lesson"""
            lesson = Lesson.query.get(int(kwargs.get(field)))
            if lesson is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = lesson
            return func(*args, **kwargs)
        return decorated_function
    return decorator