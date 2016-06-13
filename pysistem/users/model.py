# -*- coding: utf-8 -*-
from pysistem import db, app
from flask import session, g
import hashlib
import base64
import time
from flask_babel import gettext

class User(db.Model):
    """Registred user - participant or admin

    Fields:
    id -- unique user identifier
    username -- unique username, case insensitive
    password -- password, hashed with User.signpasswd
    first_name -- user's first name
    last_name -- user's last name
    email -- user's email
    role -- user's role, currently 'user' or 'admin'

    Relationships:
    submissions -- all user's submissions
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True)
    password = db.Column(db.String(64))
    first_name = db.Column(db.String(32))
    last_name = db.Column(db.String(32))
    email = db.Column(db.String(32))
    role = db.Column(db.String(8))

    submissions = db.relationship('Submission', cascade = "all,delete", backref='user')

    def __init__(self, username=None, password=None, first_name=None, last_name=None, email=None, role='user'):
        if username is None:
            id = session.get('user_id', None)
            if id is not None:
                q = User.query.filter(User.id == id).all()
                if len(q) > 0:
                    self.id = id
                    self.username = q[0].username
                    self.password = q[0].password
                    self.first_name = q[0].first_name
                    self.last_name = q[0].last_name
                    self.email = q[0].email
                    self.role = q[0].role
                    return
        self.username = username
        self.password = User.signpasswd(username, password)
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.role = role

    def __repr__(self):
        return '<User %r>' % self.username

    def is_guest(self):
        """Is this user a guest?"""
        return self.id is None

    def auth(username, password):
        """Load user identified by 'username' and 'password'
        Returns:
        Tuple(Success, User object/Error message)
        """
        signed_password = User.signpasswd(username, password)
        user = User.query.filter(
            db.func.lower(User.username) == db.func.lower(username),
            User.password == signed_password
        ).first()
        if user:
            session['user_id'] = user.id
            return True, user
        else:
            return False, gettext('auth.login.invalidcredentials')

    def signpasswd(username, password):
        """Generate password hash from username, password and application's secret key"""
        if password is None:
            return 'x'
        if type(username) is not str or type(password) is not str:
            raise TypeError("Two arguments required: (str, str)")
        hasher = hashlib.new('sha256')
        hasher.update(str.encode(password))
        hasher.update(str.encode(username.lower()))
        hasher.update(app.secret_key)
        return hasher.hexdigest()

    def exists(username):
        """Check if user by this username exists"""
        user = User.query.filter(db.func.lower(User.username) == db.func.lower(username)).first()
        return user is not None

    def get_email(self):
        """Return user's email or 'hidden' message"""
        if g.user.is_admin(user=self) or \
            (g.user.id == self.id):
            return self.email
        else:
            return '<i>%s</i>' % gettext('common.hidden')

    def check_permissions(self):
        """Return True if current user is self or current user is admin"""
        return g.user and (g.user.is_admin(user=self) or \
                (g.user.id == self.id))

    def is_admin(self, **kwargs):
        """Check if user is admin"""
        return self.role == 'admin'