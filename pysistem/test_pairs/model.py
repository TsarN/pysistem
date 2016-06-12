# -*- coding: utf-8 -*-
from pysistem import db
from pysistem.problems.model import Problem

class TestPair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input = db.Column(db.Text)
    pattern = db.Column(db.Text)

    test_group_id = db.Column(db.Integer, db.ForeignKey('test_group.id'))
    submission_logs = db.relationship('SubmissionLog', cascade="all,delete", backref="test_pair")

    def __init__(self, input='', pattern=''):
        self.input = input
        self.pattern = pattern

    def __repr__(self):
        return '<TestPair of %r>' % self.test_group.problem.name

class TestGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer)
    score_per_test = db.Column(db.Integer)
    check_all = db.Column(db.Boolean)

    test_pairs = db.relationship('TestPair', cascade = "all,delete", backref='test_group')
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))

    def __init__(self, problem=None):
        self.problem = problem
        self.score = 0
        self.score_per_test = 1
        self.check_all = False

    def __repr__(self):
        return '<TestGroup of %r>' % self.problem.name