# -*- coding: utf-8 -*-

"""Problem decorators"""

from functools import wraps

from flask import g, render_template

from pysistem.problems.model import Problem

def yield_problem(field='problem_id', yield_field='problem'):
    """Decorator
    Get problem identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If problem does not exist return 404 Not Found error
    """
    def decorator(func):
        """Decorator of yield_problem"""
        @wraps(func)
        def decorated_function(*args, **kwargs):
            """Decorated of yield_problem"""
            problem = Problem.query.get(int(kwargs.get(field)))
            if problem is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = problem
            return func(*args, **kwargs)
        return decorated_function
    return decorator

def guard_problem(field='problem'):
    """Decorator
    Check if active user has access to problem in 'field'
    If it does not -  return 403 Forbidden error
    """
    def decorator(func):
        """Decorator of guard_problem"""
        @wraps(func)
        def decorated_function(*args, **kwargs):
            """Decorated of guard_problem"""
            problem = kwargs.get(field)
            if problem is None:
                return render_template('errors/404.html'), 404
            if (len(problem.contests) > 0) and not g.user.is_admin(problem=problem):
                for assoc in problem.contests:
                    if g.now >= assoc.contest.start:
                        return func(*args, **kwargs)
                return render_template('problems/not_yet_started.html'), 403
            else:
                return func(*args, **kwargs)
        return decorated_function
    return decorator
