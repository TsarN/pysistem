# -*- coding: utf-8 -*-
from pysistem import db
from datetime import datetime

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    start = db.Column(db.DateTime, default=datetime.now)
    end = db.Column(db.DateTime, default=datetime.now)

    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'))

    def __init__(self, name=None, start=None, end=None):
        self.name = name
        self.start = start
        self.end = end

    def __repr__(self):
        if self.group_id:
            return '<Lesson %r at %r>' % (self.name, self.group.name)
        else:
            return '<Lesson %r>' % self.name