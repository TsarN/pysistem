# -*- coding: utf-8 -*-
from pysistem import db
from pysistem.problems.model import Problem

class TestPair(db.Model):
    """Test case for checking solutions. Part of test group

    Fields:
    id -- unique test pair identifier
    input -- test pair input file
    pattern -- jury's answer to test pair's input

    Relationships:
    test_group, test_group_id -- parent test group
    submission_logs -- all submission logs associated with this test

    """
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
    """Group of test cases

    Fields:
    id -- unique test group identifier
    score -- reward score for completion of _all_ associated test pairs
    score_per_test -- reward score for each associated test pair
    check_all -- check every test pair regardless of previous results

    Relationships:
    test_pairs -- children test pairs
    problem, problem_id -- parent problem

    """
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