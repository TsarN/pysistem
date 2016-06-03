from pysistem import db
from pysistem.contests.model import contest_problem_reltable
from pysistem.submissions.const import *

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    description = db.Column(db.String(256))
    statement = db.Column(db.String)
    time_limit = db.Column(db.Integer)
    memory_limit = db.Column(db.Integer)

    submissions = db.relationship('Submission', back_populates='problem')
    test_pairs = db.relationship('TestPair', back_populates='problem')
    checkers = db.relationship('Checker', back_populates='problem')

    def __init__(self, name=None, description=None, statement=None, time_limit=1000, memory_limit=65536):
        self.name = name
        self.description = description
        self.statement = statement
        self.time_limit = time_limit
        self.memory_limit = memory_limit

    def __repr__(self):
        return '<Problem %r>' % self.name

    def get_user_failed_attempts(self, user):
        from pysistem.submissions.model import Submission
        subs = Submission.query.filter(db.and_(
            self.id == Submission.problem_id,
            user.id == Submission.user_id
        )).all()
        ans = 0
        for sub in subs:
            if sub.status in [STATUS_DONE, STATUS_ACT]:
                if sub.result in [RESULT_OK]:
                    break
                if sub.tests_passed > 0:
                    if sub.result not in [RESULT_IE, RESULT_UNKNOWN]:
                        ans += 1
        return ans

    def user_succeed(self, user):
        from pysistem.submissions.model import Submission
        subs = Submission.query.filter(db.and_(
            self.id == Submission.problem_id,
            user.id == Submission.user_id
        )).all()

        for sub in subs:
            if sub.status in [STATUS_DONE, STATUS_ACT]:
                if sub.result in [RESULT_OK]:
                    return True, sub.submitted
        last_sub = None
        if len(subs) > 0:
            last_sub = subs[-1].submitted
        return False, last_sub