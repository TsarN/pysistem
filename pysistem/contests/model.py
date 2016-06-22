# -*- coding: utf-8 -*-

"""Contest models"""

from datetime import datetime

from flask import g

from pysistem import db

class ContestProblemAssociation(db.Model):
    """Helper class to associate contests and problems between each other
    In normal circumstances, it acts like Problem

    Fields:
    prefix -- Problem's prefix in contest

    Relationships:
    contest, contest_id -- Contest
    problem, problem_id -- Problem
    """
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
            return '<ContestProblemAssociation Unknown>'

    def __getattr__(self, attr):
        if attr[0] != '_':
            return self.problem.__getattribute__(attr)
        raise AttributeError

class Contest(db.Model):
    """Collection of problems and participants

    Fields:
    id -- unique contest identifier
    name -- contest name
    rules -- contest ruleset, currently either 'acm' (ACM/ICPC rules) or 'roi' (ROI rules)
    start -- contest start datetime
    end -- contest end datetime
    freeze -- contest 'freeze scoreboard' datetime
    unfreeze_after_end -- if scoreboard should be automatically unfreezed after finish

    Relationships:
    problems -- problems in contest (ContestProblemAssociation)
    groups -- groups to which contest is attached (GroupContestAssociation)
    lessons -- attached lessons (Lesson)
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    rules = db.Column(db.String(8))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    freeze = db.Column(db.DateTime)
    unfreeze_after_end = db.Column(db.Boolean)

    problems = db.relationship('ContestProblemAssociation',
                               back_populates='contest',
                               order_by='ContestProblemAssociation.prefix')
    groups = db.relationship('GroupContestAssociation', back_populates='contest')
    lessons = db.relationship('Lesson', cascade='all,delete', backref='contest')

    def __init__(self, name=None, rules='acm', start=None, end=None,
                 freeze=None, unfreeze_after_end=False):
        self.name = name
        self.rules = rules if rules in contest_rulesets.keys() else 'acm'
        self.start = start
        self.end = end
        self.freeze = freeze
        self.unfreeze_after_end = unfreeze_after_end

    def __repr__(self):
        return '<Contest %r>' % self.name

    def get_freeze_time(self, admin=True):
        """Get time after which no submissions alter scoreboard"""
        freeze = self.freeze
        if (self.unfreeze_after_end and (datetime.now() > self.end)) \
            or (admin and g.user.is_admin(contest=self)):
            freeze = self.end
        return freeze

    def is_admin_frozen(self):
        """Is active user an admin of this contest AND if scoreboard is frozen"""
        return g.user.is_admin(contest=self) and self.is_frozen()

    def is_frozen(self):
        """If scoreboard is frozen"""
        if self.unfreeze_after_end and (datetime.now() > self.end):
            return False
        if datetime.now() < self.freeze:
            return False
        return True

    def rate_user(self, user, do_freeze=True):
        """Get user's score in contests"""
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
                succ = problem.user_succeed(user, freeze=freeze)
                if succ[0]:
                    solved += 1
                    penalty += problem.get_user_failed_attempts(user, freeze=freeze) * 20
                    penalty += max(0, (succ[1] - self.start).total_seconds() // 60)
            return solved, int(penalty)

contest_rulesets = {
    "acm": "ACM/ICPC",
    "roi": "ROI"
}
