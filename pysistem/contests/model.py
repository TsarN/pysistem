# -*- coding: utf-8 -*-

"""Contest models"""

from datetime import datetime

from flask import g

from pysistem import db
from pysistem.submissions.const import STATUS_DONE

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
                               back_populates='contest', lazy="dynamic",
                               order_by='ContestProblemAssociation.prefix', cascade='all,delete')
    groups = db.relationship('GroupContestAssociation', back_populates='contest',
                             cascade='all,delete', lazy="dynamic")
    lessons = db.relationship('Lesson', cascade='all,delete',
                              lazy="dynamic", backref='contest')

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

    def rate_user(self, user, do_freeze=True, rules=None, subs=None):
        """Get user's score in contests"""
        if do_freeze:
            freeze = self.get_freeze_time()
        else:
            freeze = None
        rules = rules or self.rules
        if rules == 'roi':
            score = 0
            if subs:
                for problem in self.problems:
                    score += problem.user_score(user, freeze=freeze, subs=subs[problem.id])[0]
            else:
                for problem in self.problems:
                    score += problem.user_score(user, freeze=freeze)[0]
            return (score,)
        else:
            solved, penalty = 0, 0
            if subs:
                for problem in self.problems:
                    succ = problem.user_score(user, freeze=freeze, subs=subs[problem.id])
                    if succ[0] and (succ[0] >= problem.get_max_score()):
                        solved += 1
                        penalty += problem.get_user_failed_attempts(user, freeze=freeze,
                                                                    subs=subs[problem.id]) * 20
                        penalty += max(0, (succ[1] - self.start).total_seconds() // 60)
            else:
                for problem in self.problems:
                    succ = problem.user_score(user, freeze=freeze)
                    if succ[0] and (succ[0] >= problem.get_max_score()):
                        solved += 1
                        penalty += problem.get_user_failed_attempts(user, freeze=freeze) * 20
                        penalty += max(0, (succ[1] - self.start).total_seconds() // 60)
            return solved, int(penalty)

    def get_places(self):
        from pysistem.submissions.model import Submission
        from pysistem.problems.model import Problem
        users = {}
        query = Submission.query.filter(db.and_(
                 Submission.status == STATUS_DONE,
                 Submission.problem.any(Problem.contest_id == self.id)))
        for submission in query:
            user_id = submission.user_id
            if user_id and user_id not in users:
                users[user_id] = self.rate_user(submission.user)
        users_sorted = [(users[u], u) for u in users]
        if self.rules == 'acm':
            users_sorted = [((u[0][0], -u[0][1]), u[1]) for u in users_sorted]
        users_sorted.sort(reverse=True)

        user_places = {}
        current_place = 0
        supposed_place = 0
        last_val = None
        for user in users_sorted:
            supposed_place += 1
            if user[0] != last_val:
                last_val = user[0]
                current_place = supposed_place
            user_places[user[1]] = current_place
        return user_places

contest_rulesets = {
    "acm": "ACM/ICPC",
    "roi": "ROI"
}
