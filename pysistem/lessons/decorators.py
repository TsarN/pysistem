# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from pysistem.lessons.model import Lesson
from pysistem import db

def yield_lesson(field='id', yield_field='lesson'):
    """Decorator
    Get lesson identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If lesson does not exist return 404 Not Found error
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            lesson = Lesson.query.get(int(kwargs.get(field)))
            if lesson is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = lesson
            return f(*args, **kwargs)
        return decorated_function
    return decorator