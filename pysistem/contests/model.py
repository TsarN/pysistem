from pysistem import db
from datetime import datetime

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

    def rate_user(self, user):
        solved, penalty = 0, 0
        for problem in self.problems:
            s = problem.user_succeed(user)
            if s[0]:
                solved += 1
                penalty += problem.get_user_failed_attempts(user) * 20
                penalty += max(0, (s[1] - self.start).total_seconds() // 60)
        return solved, int(penalty)