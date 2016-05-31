from pysistem import db
from pysistem.problems.model import Problem

class TestPair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input = db.Column(db.String)
    pattern = db.Column(db.String)

    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    problem = db.relationship('Problem', back_populates='test_pairs')

    def __init__(self, input='', pattern='', problem=None):
        self.input = input
        self.pattern = pattern

        if type(problem) is int:
            problem = Problem.query.get(problem)

        self.problem = problem

    def __repr__(self):
        return '<TestPair of %r>' % self.problem.name