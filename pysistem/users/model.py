# -*- coding: utf-8 -*-
from pysistem import db, app
from flask import session, g
import hashlib
import base64
import time
from flask_babel import gettext
from pysistem.groups.model import Group, GroupUserAssociation, GroupContestAssociation
from pysistem.problems.model import Problem
from pysistem.contests.model import Contest

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
    groups -- all user's groups (GroupUserAssociation)
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True)
    password = db.Column(db.String(64))
    first_name = db.Column(db.String(32))
    last_name = db.Column(db.String(32))
    email = db.Column(db.String(32))
    role = db.Column(db.String(8))

    submissions = db.relationship('Submission', cascade = "all,delete", backref='user')
    groups = db.relationship('GroupUserAssociation', back_populates='user')

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
        """Check if user is admin
        Keyword arguments (all optional):
        contest, problem, submission, test_group, test_pair, user, group

        All keyword arguments identify object against which
        test admin rights.
        """
        if self.role == 'admin':
            return True

        if not kwargs:
            return False

        admin_groups = GroupUserAssociation.query.filter(db.and_(
            GroupUserAssociation.user_id == self.id,
            GroupUserAssociation.role == 'admin')).all()

        admin_groups_ids = [x.group_id for x in admin_groups]

        group = kwargs.get('group')
        if group:
            if type(group) is not int:
                group_id = group.id
            else:
                group_id = group
            if group_id in admin_groups_ids:
                return True
            else:
                return False

        contest = kwargs.get('contest')
        if contest:
            if type(contest) is not int:
                contest_id = contest.id
            else:
                contest_id = contest
            if GroupContestAssociation.query.filter(db.and_( \
                GroupContestAssociation.contest_id == contest_id, \
                GroupContestAssociation.group_id.in_(admin_groups_ids))).first():
                return True
            else:
                return False

        problem = kwargs.get('problem')
        if problem:
            if type(problem) is not int:
                problem_id = problem.id
            else:
                problem_id = problem
            if Problem.query.filter(db.and_( \
                Problem.id == problem_id, \
                Problem.contests.any(Contest.groups.any( \
                GroupContestAssociation.group_id.in_(admin_groups_ids))))).first():
                return True
            else:
                return False

        user = kwargs.get('user')
        if user:
            if type(user) is not int:
                user_id = user.id
            else:
                user_id = user
            if GroupContestAssociation.query.filter(db.and_( \
                GroupUserAssociation.user_id == user_id, \
                GroupUserAssociation.group_id.in_(admin_groups_ids) \
                )).first():
                return True
            else:
                return False

        test_group = kwargs.get('test_group')
        if test_group:
            return self.is_admin(problem=test_group.problem)

        test_pair = kwargs.get('test_pair')
        if test_pair:
            return self.is_admin(test_group=test_pair.test_group)

        submission = kwargs.get('submission')
        if submission:
            if type(submission) is list:
                submission = submission[0]
            return self.is_admin(user=submission.user) or \
                   self.is_admin(problem=submission.problem)

        return False