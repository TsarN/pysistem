# -*- coding: utf-8 -*-
from pysistem import db
from datetime import datetime
from flask import g

contest_problem_reltable = db.Table('contest_problem_reltable',
    db.Column('contest_id', db.Integer, db.ForeignKey('contest.id'), nullable=False),
    db.Column('problem_id', db.Integer, db.ForeignKey('problem.id'), nullable=False),
    db.PrimaryKeyConstraint('contest_id', 'problem_id'))

class Contest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    rules = db.Column(db.String(8))
    start = db.Column(db.DateTime, default=datetime.now)
    end = db.Column(db.DateTime, default=datetime.now)
    freeze = db.Column(db.DateTime, default=datetime.now)
    unfreeze_after_end = db.Column(db.Boolean)

    problems = db.relationship('Problem',
        secondary=contest_problem_reltable,
        cascade = "all,delete-orphan", 
        backref=db.backref('contests'))

    def __init__(self, name=None, rules='acm', start=None, end=None, freeze=None, unfreeze_after_end=False):
        self.name = name
        self.rules = rules
        self.start = start
        self.end = end
        self.freeze = freeze
        self.unfreeze_after_end = unfreeze_after_end

    def __repr__(self):
        return '<Contest %r>' % self.name

    def get_freeze_time(self, admin=True):
        freeze = self.freeze
        if (self.unfreeze_after_end and (datetime.now() > self.end)) \
            or (admin and (g.user.role == 'admin')):
            freeze = None
        return freeze

    def is_frozen(self):
        freeze = self.get_freeze_time()
        return freeze and (freeze < datetime.now())

    def is_admin_frozen(self):
        freeze = self.get_freeze_time(admin=False)
        return freeze and (freeze < datetime.now())

    def rate_user(self, user):
        solved, penalty = 0, 0
        freeze = self.get_freeze_time()
        for problem in self.problems:
            s = problem.user_succeed(user, freeze=freeze)
            if s[0]:
                solved += 1
                penalty += problem.get_user_failed_attempts(user, freeze=freeze) * 20
                penalty += max(0, (s[1] - self.start).total_seconds() // 60)
        return solved, int(penalty)