# -*- coding: utf-8 -*-
from pysistem import db, app
from flask import session, g
import hashlib
from flask_babel import gettext

class User(db.Model):
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
        return self.id is None

    def auth(username, password):
        signed_password = User.signpasswd(username, password)
        q = User.query.filter(
            db.func.lower(User.username) == db.func.lower(username),
            User.password == signed_password
        ).all()
        if len(q) > 0:
            session['user_id'] = q[0].id
            return True, q[0]
        else:
            return False, gettext('auth.login.invalidcredentials')

    def signpasswd(username, password):
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
        q = User.query.filter(db.func.lower(User.username) == db.func.lower(username)).all()
        return len(q) > 0

    def get_email(self):
        if (g.user.role == 'admin') or \
            (g.user.id == self.id):
            return self.email
        else:
            return '<i>%s</i>' % gettext('common.hidden')

    def check_permissions(self):
        return (g.user.role == 'admin') or \
                (g.user.id == self.id)