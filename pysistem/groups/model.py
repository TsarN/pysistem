# -*- coding: utf-8 -*-

"""Group models"""

from datetime import datetime

from pysistem import db
from pysistem.lessons.model import Lesson

class GroupUserAssociation(db.Model):
    """Helper class to associate groups and users between each other
    By default it acts like User

    Fields:
    role -- user's role in group. Currently either 'user' or 'admin'

    Relationships:
    group, group_id -- Group
    user, user_id -- User
    """
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    role = db.Column(db.String(8))

    group = db.relationship('Group', back_populates='users')
    user = db.relationship('User', back_populates='groups')
    def __init__(self, role=None):
        self.role = role

    def __repr__(self):
        if self.user and self.group:
            return '<Group=%r User=%r>' % (self.group.name, self.user.username)
        else:
            return '<GroupUserAssociation Unknown>'

    def __getattr__(self, attr):
        if attr[0] != '_':
            return self.user.__getattribute__(attr)
        raise AttributeError

class GroupContestAssociation(db.Model):
    """Helper class to associate groups and contests between each other
    By default it acts like Contest

    Relationships:
    group, group_id -- Group
    contest, contest_id -- Contest
    """
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), primary_key=True)

    group = db.relationship('Group', back_populates='contests')
    contest = db.relationship('Contest', back_populates='groups')

    def __repr__(self):
        if self.contest and self.group:
            return '<Group=%r Contest=%r>' % (self.group.name, self.contest.name)
        else:
            return '<GroupContestAssociation Unknown>'

    def __getattr__(self, attr):
        if attr[0] != '_':
            return self.contest.__getattribute__(attr)
        raise AttributeError

class Group(db.Model):
    """Collection of users and contests

    Fields:
    id -- unique group identifier
    name -- group name

    Relationships:
    users -- attached users (GroupUserAssociation)
    contests -- attached contests (GroupContestAssociation)
    lessons -- attached lessons (Lesson)
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))

    users = db.relationship('GroupUserAssociation', cascade='all,delete',
                            back_populates='group')
    contests = db.relationship('GroupContestAssociation', cascade='all,delete',
                               back_populates='group')
    lessons = db.relationship('Lesson', cascade='all,delete', backref='group',
                              order_by=Lesson.start.desc())

    def __init__(self, name=None):
        self.name = name

    def __repr__(self):
        return '<Group %r>' % self.name

    def get_current_lessons(self):
        """Return currently ongoing Lessons"""
        now = datetime.now()
        return Lesson.query.filter(db.and_(Lesson.group_id == self.id, \
               Lesson.start <= now, Lesson.end >= now)).all()
