from pysistem import db

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
