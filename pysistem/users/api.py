# -*- coding: utf-8 -*-
from pysistem.users.model import User
from flask import session, g, redirect, url_for, request, Blueprint
from pysistem import app, db, g
from pysistem.api import apires, fieldify
from functools import wraps

api = Blueprint('users_api', __name__, url_prefix='/api/users')

allowed_user_fields = ("id", "username", "first_name", "last_name", "email")
default_user_fields = ("id", "username")

def yield_user(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        id = kwargs.get('user_id', None)
        username = kwargs.get('username', None)
        user = None
        if id is not None:
            user = User.query.get(id)
            del kwargs['user_id']
        elif username is not None:
            user = User.query.filter(
                db.func.lower(User.username) == db.func.lower(username)).first()
            del kwargs['username']
        if user is None:
            return apires({
                    "error": -1,
                    "message": "No such user"
                }, 404)
        fields = kwargs.get('fields', list(default_user_fields))
        for field in fields:
            if field not in allowed_user_fields:
                return apires({
                    "error": -2,
                    "message": "No such field: %s" % field
                }, 404)
        kwargs['user'] = user
        kwargs['fields'] = fields
        return f(**kwargs)
    return decorated_function

def get_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email
    }

@api.route('/get', methods=['GET'])
@api.route('/get/<int:user_id>', methods=['GET'])
@api.route('/get/<username>', methods=['GET'])
@api.route('/get/fields/<str_list:fields>', methods=['GET'])
@api.route('/get/<int:user_id>/fields/<str_list:fields>', methods=['GET'])
@api.route('/get/<username>/fields/<str_list:fields>', methods=['GET'])
@yield_user
@fieldify()
def get(**_):
    return get_users(_)
    

@api.route('/list', methods=['GET'])
@api.route('/list/fields/<str_list:fields>', methods=['GET'])
@fieldify(default=default_user_fields, allowed=allowed_user_fields)
def list_(**_):
    return [get_user(user) for user in User.query.all()]