# -*- coding: utf-8 -*-
from pysistem import db
from datetime import datetime
from flask import g
from flask_babel import gettext

class ContestProblemAssociation(db.Model):
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), primary_key=True)
    prefix = db.Column(db.String(8))
    contest = db.relationship('Contest',
        back_populates='problems')
    problem = db.relationship('Problem',
        back_populates='contests')

    def __init__(self, prefix=None):
        self.prefix = prefix or ''

    def __repr__(self):
        if self.contest and self.problem:
            return '<Contest=%r, Problem=%r>' % (self.contest.name, self.name)
        else:
            return '<ContestProblemAssociation>'

    def __getattr__(self, attr):
        if attr[0] != '_':
            return self.problem.__getattribute__(attr)
        raise AttributeError

class Contest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    rules = db.Column(db.String(8))
    start = db.Column(db.DateTime, default=datetime.now)
    end = db.Column(db.DateTime, default=datetime.now)
    freeze = db.Column(db.DateTime, default=datetime.now)
    unfreeze_after_end = db.Column(db.Boolean)

    problems = db.relationship('ContestProblemAssociation',
        back_populates='contest', order_by='ContestProblemAssociation.prefix')

    def __init__(self, name=None, rules='acm', start=None, end=None, freeze=None, unfreeze_after_end=False):
        self.name = name
        self.rules = rules if rules in contest_rulesets.keys() else 'acm'
        self.start = start
        self.end = end
        self.freeze = freeze
        self.unfreeze_after_end = unfreeze_after_end

    def __repr__(self):
        return '<Contest %r>' % self.name

    def get_freeze_time(self, admin=True):
        freeze = self.freeze
        if (self.unfreeze_after_end and (datetime.now() > self.end)) \
            or (admin and g.user.is_admin(contest=self)):
            freeze = self.end
        return freeze

    def is_frozen(self):
        return g.user.is_admin(contest=self) and self.is_admin_frozen()

    def is_admin_frozen(self):
        if self.unfreeze_after_end and (datetime.now() > self.end):
            return False
        if datetime.now() < self.freeze:
            return False
        return True

    def rate_user(self, user, do_freeze=True):
        if do_freeze:   
            freeze = self.get_freeze_time()
        else:
            freeze = None
        if self.rules == 'roi':
            score = 0
            for problem in self.problems:
                score += problem.user_succeed(user, freeze=freeze)[0]
            return (score,)
        else:
            solved, penalty = 0, 0
            for problem in self.problems:
                s = problem.user_succeed(user, freeze=freeze)
                if s[0]:
                    solved += 1
                    penalty += problem.get_user_failed_attempts(user, freeze=freeze) * 20
                    penalty += max(0, (s[1] - self.start).total_seconds() // 60)
            return solved, int(penalty)

contest_rulesets = {
    "acm": "ACM/ICPC",
    "roi": "ROI"
}