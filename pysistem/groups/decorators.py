# -*- coding: utf-8 -*-
"""Group decorators"""

from functools import wraps

from flask import g, render_template
from pysistem.groups.model import Group, GroupUserAssociation
from pysistem import db

def yield_group(field='group_id', yield_field='group'):
    """Decorator
    Get group identified by 'field' keyword argument
    and save it to 'yield_field' keyword argument.
    If group does not exist return 404 Not Found error
    """
    def decorator(func):
        """Decorator of yield_group()"""
        @wraps(func)
        def decorated_function(*args, **kwargs):
            """Decorated of yield_group()"""
            group = Group.query.get(int(kwargs.get(field)))
            if group is None:
                return render_template('errors/404.html'), 404
            kwargs[yield_field] = group
            return func(*args, **kwargs)
        return decorated_function
    return decorator

def requires_group_membership(field='group_id', object_field='group'):
    """Decorator
    Display page if user in group, else return 403 Forbidden error
    """
    def decorator(func):
        """Decorator of requires_group_membership()"""
        @wraps(func)
        def decorated_function(*args, **kwargs):
            """Decorated of requires_group_membership()"""
            if g.user.is_admin():
                return func(*args, **kwargs)
            if not g.user.id:
                return render_template('errors/403.html'), 403

            group = kwargs.get(object_field)
            if not isinstance(group, Group):
                group_id = kwargs.get(field)
                if isinstance(group_id, int):
                    group = Group.query.get(group_id)
                else:
                    group = None
            if not group:
                return render_template('errors/404.html'), 404

            assoc = GroupUserAssociation.query.filter(db.and_( \
                GroupUserAssociation.group_id == group.id, \
                GroupUserAssociation.user_id == g.user.id)).first()

            if not assoc:
                return render_template('errors/403.html'), 403
            return func(*args, **kwargs)
        return decorated_function
    return decorator
