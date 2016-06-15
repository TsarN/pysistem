# -*- coding: utf-8 -*-
from pysistem import db
from datetime import datetime
import re

def parseInt(sin):
    # https://gist.github.com/lsauer/6088767
    m = re.search(r'^(\d+)[.,]?\d*?', str(sin))
    return int(m.groups()[-1]) if m and not callable(sin) else None

class LessonUserAssociation(db.Model):
    """Helper class to associate lessons and users between each other
    By default it acts like User

    Fields:
    mark -- user's mark for lesson
    points -- user's points for lesson

    Relationships:
    lesson, lesson_id -- Lesson
    user, user_id -- User
    """
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    mark = db.Column(db.String(4))
    points = db.Column(db.Integer)

    lesson = db.relationship('Lesson', back_populates='users')
    user = db.relationship('User', back_populates='lessons')

    def __init__(self, mark=None, points=None):
        self.mark = mark
        self.points = points

    def __repr__(self):
        if self.user and self.lesson:
            return '<Lesson=%r User=%r>' % (self.lesson.name, self.user.username)
        else:
            return '<LessonUserAssociation Unknown>'

    def __getattr__(self, attr):
        if attr[0] != '_':
            return self.user.__getattribute__(attr)
        raise AttributeError

    def int_mark(self):
        return parseInt(self.mark)


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    start = db.Column(db.DateTime, default=datetime.now)
    end = db.Column(db.DateTime, default=datetime.now)

    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'))

    users = db.relationship('LessonUserAssociation', back_populates='lesson')

    def __init__(self, name=None, start=None, end=None):
        self.name = name
        self.start = start
        self.end = end

    def __repr__(self):
        if self.group_id:
            return '<Lesson %r at %r>' % (self.name, self.group.name)
        else:
            return '<Lesson %r>' % self.name