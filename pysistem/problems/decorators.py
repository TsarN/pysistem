# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext
from pysistem.problems.model import Problem

def yield_problem(field='id', yield_field='problem'):
    # Yield problem identified by 'field' to 'yield_field'
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            problem = Problem.query.get(int(kwargs.get(field)))
            if problem is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = problem
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def guard_problem(field='problem'):
    # Guard problem 'problem' from unauthorized access
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            problem = kwargs.get(field)
            if problem is None:
                return render_template('errors/404.html'), 404
            if (len(problem.contests) > 0) and g.user.is_admin(problem=problem):
                for contest in problem.contests:
                    if g.now >= contest.start:
                        return f(*args, **kwargs)
                return render_template('problems/not_yet_started.html'), 403
            else:
                return f(*args, **kwargs)
        return decorated_function
    return decorator