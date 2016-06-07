# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext
from pysistem.test_pairs.model import TestPair

def yield_test_pair(field='id', yield_field='test'):
    # Yield test pair identified by 'field' to 'yield_field'
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            test = TestPair.query.get(int(kwargs.get(field)))
            if test is None:
                return render_template('errors/404.html')
            kwargs[yield_field] = test
            return f(*args, **kwargs)
        return decorated_function
    return decorator