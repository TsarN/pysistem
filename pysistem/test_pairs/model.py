from pysistem import db
from pysistem.problems.model import Problem

class TestPair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input = db.Column(db.String(2**20))
    pattern = db.Column(db.String(2**20))

    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))

    def __init__(self, input='', pattern='', problem=None):
        self.input = input
        self.pattern = pattern

        if type(problem) is int:
            problem = Problem.query.get(problem)

        self.problem = problem

    def __repr__(self):
        return '<TestPair of %r>' % self.problem.name