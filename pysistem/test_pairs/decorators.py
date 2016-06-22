# -*- coding: utf-8 -*-

"""Test pairs and groups decorators"""

from functools import wraps

from flask import render_template

from pysistem.test_pairs.model import TestPair, TestGroup

def yield_test_pair(field='test_pair_id', yield_field='test'):
    """Decorator
    Get test pair identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If test pair does not exist return 404 Not Found error
    """
    def decorator(func):
        """Decorator of yield_test_pair"""
        @wraps(func)
        def decorated_function(*args, **kwargs):
            """Decorated of yield_test_pair"""
            test = TestPair.query.get(int(kwargs.get(field)))
            if test is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = test
            return func(*args, **kwargs)
        return decorated_function
    return decorator

def yield_test_group(field='test_group_id', yield_field='test_group'):
    """Decorator
    Get test group identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If test group does not exist return 404 Not Found error
    """
    def decorator(func):
        """Decorator of yield_test_group"""
        @wraps(func)
        def decorated_function(*args, **kwargs):
            """Decorated of yield_test_group"""
            test_group = TestGroup.query.get(int(kwargs.get(field)))
            if test_group is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = test_group
            return func(*args, **kwargs)
        return decorated_function
    return decorator
