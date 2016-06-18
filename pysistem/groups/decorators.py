# -*- coding: utf-8 -*-
from functools import wraps

from flask import g, flash, redirect, url_for, request, render_template
from flask_babel import gettext
from pysistem.groups.model import Group, GroupUserAssociation
from pysistem import db

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

def requires_group_membership(field='id', object_field='group'):
    """Decorator
    Display page if user in group, else return 403 Forbidden error
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if g.user.is_admin():
                return f(*args, **kwargs)
            if not g.user.id:
                return render_template('errors/403.html'), 403

            group = kwargs.get(object_field)
            if type(group) is not Group:
                group_id = kwargs.get(field)
                if type(group_id) is int:
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
            return f(*args, **kwargs)
        return decorated_function
    return decorator