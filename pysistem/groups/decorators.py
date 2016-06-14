# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext
from pysistem.groups.model import Group

def yield_group(field='id', yield_field='group'):
    """Decorator
    Get group identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If group does not exist return 404 Not Found error
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            group = Group.query.get(int(kwargs.get(field)))
            if group is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = group
            return f(*args, **kwargs)
        return decorated_function
    return decorator