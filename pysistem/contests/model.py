from pysistem import db

class Contest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    rules = db.Column(db.String(8))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)

    def __init__(self, name=None, rules=None, start=None, end=None):
        self.name = name
        self.rules = rules
        self.start = start
        self.end = end

    def __repr__(self):
        return '<Contest %r>' % self.name