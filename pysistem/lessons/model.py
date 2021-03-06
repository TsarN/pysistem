# -*- coding: utf-8 -*-

"""Lessons model"""

import re

from flask_babel import gettext

from pysistem import db
from pysistem.lessons.const import AUTO_MARK_SCORE, AUTO_MARK_PLACE, AUTO_MARK_SOLVED

def parse_int(sin):
    """Javascript-like parseInt"""
    # https://gist.github.com/lsauer/6088767
    search = re.search(r'^(\d+)[.,]?\d*?', str(sin))
    return int(search.groups()[-1]) if search and not callable(sin) else None

def babel_translations(): # pragma: no cover
    gettext("lessons.automarks.score")
    gettext("lessons.automarks.score.atleast")
    gettext("lessons.automarks.place")
    gettext("lessons.automarks.place.atleast")
    gettext("lessons.automarks.solved")
    gettext("lessons.automarks.solved.atleast")


class LessonUserAssociation(db.Model):
    """Helper class to associate lessons and users between each other
    By default it acts like User

    Fields:
    mark -- user's mark for lesson

    Relationships:
    lesson, lesson_id -- Lesson
    user, user_id -- User
    """
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    mark = db.Column(db.String(4))

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
        """Turn string mark into int"""
        return parse_int(self.mark)


class AutoMark(db.Model):
    """Automatic mark and point pattern

    Fields:
    id -- unique auto mark id
    type -- type of auto mark, as in pysistem.lessons.const

    Relationships:
    lesson, lesson_id -- attached lesson
    """
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Integer)
    required = db.Column(db.Integer)
    mark = db.Column(db.String(4))
    points = db.Column(db.Integer)

    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'))

    def __init__(self, type=AUTO_MARK_SCORE, required=0, mark=None, points=0):
        if type == "score":
            type = AUTO_MARK_SCORE
        if type == "place":
            type = AUTO_MARK_PLACE
        if type == "solved":
            type = AUTO_MARK_SOLVED
        self.type = type
        self.required = required
        self.mark = mark
        self.points = points

    def __repr__(self):
        if self.lesson_id:
            return '<AutoMark of %r>' % self.lesson.name
        return '<AutoMark>'

class Lesson(db.Model):
    """An event that has start, end, attached contest and attendance

    Fields:
    id -- unique lesson id
    name -- lesson name
    start -- lesson's start datetime
    end -- lesson's end datetime
    auto_marks_applied -- automarks already applied?

    Relationships:
    group, group_id -- group, whose lesson it is
    contest, contest_id -- attached contest
    users -- lesson's attendants (LessonUserAssociation)
    auto_marks -- lesson's auto marks settings (AutoMark)
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    start = db.Column(db.DateTime)
    end = db.Column(db.DateTime)
    auto_marks_applied = db.Column(db.Boolean)

    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'))

    users = db.relationship('LessonUserAssociation', back_populates='lesson',
                            cascade="all,delete", lazy="dynamic")
    auto_marks = db.relationship('AutoMark', cascade="all,delete", lazy="dynamic",
                                 backref='lesson', order_by=AutoMark.required.desc())

    def __init__(self, name=None, start=None, end=None):
        self.name = name
        self.start = start
        self.end = end
        self.auto_marks_applied = False

    def __repr__(self):
        if self.group_id:
            return '<Lesson %r at %r>' % (self.name, self.group.name)
        else:
            return '<Lesson %r>' % self.name

    def get_automarks(self, **kwargs):
        """Return (mark, points) by user's score, place or solved problems"""
        allowed = ("score", "place", "solved")
        valid_keys = list(filter(lambda x: x in allowed, kwargs.keys()))
        params = len(valid_keys)
        if params == 0:
            return (None, 0)
        if params > 1:
            results = []
            for key in valid_keys:
                results.append(self.get_automarks(**dict(((key, kwargs[key]),))))
            return max(results, key=lambda x: (x[1], x[0] or ''))
        auto_marks = self.auto_marks.filter(AutoMark.type == allowed.index(valid_keys[0])).all()
        if valid_keys[0] == "place":
            for mark in auto_marks[::-1]:
                if mark.required >= kwargs[valid_keys[0]]:
                    return (mark.mark, mark.points)
        else:
            for mark in auto_marks:
                if mark.required <= kwargs[valid_keys[0]]:
                    return (mark.mark, mark.points)
        return (None, 0)
