# -*- coding: utf-8 -*-
from pysistem import db

class GroupUserAssociation(db.Model):
    """Helper class to associate groups and users between each other

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

class GroupContestAssociation(db.Model):
    """Helper class to associate groups and contests between each other

    Relationships:
    group, group_id -- Group
    contest, contest_id -- Contest
    """
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), primary_key=True)
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), primary_key=True)

    group = db.relationship('Group', back_populates='contests')
    contest = db.relationship('Contest', back_populates='groups')

    def __init__(self): pass
    def __repr__(self):
        if self.contest and self.group:
            return '<Group=%r Contest=%r>' % (self.group.name, self.contest.name)
        else:
            return '<GroupContestAssociation Unknown>'

class Group(db.Model):
    """Collection of users and contests

    Fields:
    id -- unique group identifier
    name -- group name

    Relationships:
    users -- attached users (GroupUserAssociation)
    contests -- attached contests (GroupContestAssociation)
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))

    users = db.relationship('GroupUserAssociation', back_populates='group')
    contests = db.relationship('GroupContestAssociation', back_populates='group')

    def __init__(self, name=None):
        self.name = name

    def __repr__(self):
        return '<Group %r>' % self.name