# -*- coding: utf-8 -*-
from pysistem import db
from pysistem.contests.model import contest_problem_reltable
from pysistem.submissions.const import *
import pickle
import gzip
import io
import hashlib

EXPORTVER = 1

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    description = db.Column(db.String(256))
    statement = db.Column(db.Text)
    time_limit = db.Column(db.Integer)
    memory_limit = db.Column(db.Integer)

    submissions = db.relationship('Submission', cascade = "all,delete", backref='problem')
    test_pairs = db.relationship('TestPair', cascade = "all,delete", backref='problem')
    checkers = db.relationship('Checker', cascade = "all,delete", backref='problem')

    def __init__(self, name=None, description=None, statement=None, time_limit=1000, memory_limit=65536):
        self.name = name
        self.description = description
        self.statement = statement
        self.time_limit = time_limit
        self.memory_limit = memory_limit

    def __repr__(self):
        return '<Problem %r>' % self.name

    def get_user_failed_attempts(self, user, freeze=None):
        from pysistem.submissions.model import Submission
        subs = Submission.query.filter(db.and_(
            self.id == Submission.problem_id,
            user.id == Submission.user_id
        )).all()
        ans = 0
        for sub in subs:
            if freeze and sub.submitted > freeze:
                break
            if sub.status in [STATUS_DONE, STATUS_ACT]:
                if sub.result in [RESULT_OK]:
                    break
                if sub.tests_passed > 0:
                    if sub.result not in [RESULT_IE, RESULT_UNKNOWN]:
                        ans += 1
        return ans

    def user_succeed(self, user, freeze=None):
        from pysistem.submissions.model import Submission
        subs = Submission.query.filter(db.and_(
            self.id == Submission.problem_id,
            user.id == Submission.user_id
        )).all()

        last_sub = None

        for sub in subs:
            if freeze and sub.submitted > freeze:
                break
            if sub.status in [STATUS_DONE, STATUS_ACT]:
                if sub.tests_passed > 0:
                    if sub.result not in [RESULT_IE, RESULT_UNKNOWN]:
                        last_sub = sub.submitted
                if sub.result in [RESULT_OK]:
                    return True, sub.submitted
        return False, last_sub

    def user_status(self, user, color=True, failed_test=False, only_color=False):
        from pysistem.submissions.model import Submission
        subs = Submission.query.filter(db.and_(
            self.id == Submission.problem_id,
            user.id == Submission.user_id
        )).all()

        attempted = None

        for sub in subs:
            if sub.status in [STATUS_DONE, STATUS_ACT]:
                if sub.result in [RESULT_OK]:
                    return sub.get_str_result(color=color, failed_test=failed_test, only_color=only_color)
                elif sub.result not in [RESULT_IE, RESULT_UNKNOWN]:
                    if sub.tests_passed > 0:
                        attempted = sub
            elif sub.status in [STATUS_CHECKING]:
                attempted = sub
        if attempted:
            return attempted.get_str_result(color=color, failed_test=failed_test, only_color=only_color)
        else:
            return ""
        

    def export_gzip(self):
        to_write = pickle.dumps({
            'name': self.name,
            'time_limit': self.time_limit,
            'memory_limit': self.memory_limit,
            'description': self.description,
            'statement': self.statement,
            'checkers': [{
                'name': checker.name,
                'lang': checker.lang,
                'source': checker.source
            } for checker in self.checkers if checker.status in [STATUS_DONE, STATUS_ACT]],
            'test_pairs': [{
                'input': test.input,
                'pattern': test.pattern
            } for test in self.test_pairs],
            'version': EXPORTVER
        })

        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='wb') as f:
            f.write(to_write)
        return out.getvalue()

    def import_gzip(self, data):
        from pysistem.checkers.model import Checker
        from pysistem.test_pairs.model import TestPair
        f = io.BytesIO()
        f.write(data)
        f.seek(0)
        input_f = gzip.GzipFile(fileobj=f, mode='rb')
        data = pickle.load(input_f)
        if data.get('version', 0) != EXPORTVER:
            return False
        self.name = data.get('name', self.name)
        self.time_limit = data.get('time_limit', self.time_limit)
        self.memory_limit = data.get('memory_limit', self.memory_limit)
        self.description = data.get('description', self.description)
        self.statement = data.get('statement', self.statement)
        for checker in data.get('checkers', ()):
            c = Checker(
                checker['name'],
                checker['source'],
                self,
                checker['lang']
            )
            db.session.add(c)
            db.session.commit()
            c.compile()
        for test in data.get('test_pairs', ()):
            db.session.add(TestPair(
                test['input'],
                test['pattern'],
                self
            ))
        db.session.commit()
        return True

    def transliterate_name(self):
        fallback = 'problem' + str(self.id)
        try:
            from transliterate import detect_language, translit
            import unicodedata
            import re
        except:
            return fallback
        language_code = detect_language(self.name)
        trans = self.name
        if language_code:
            trans = translit(self.name, language_code, reversed=True)
        slug = unicodedata.normalize('NFKD', trans) \
                          .encode('ascii', 'ignore') \
                          .decode('ascii')
        slug = re.sub('[^\w\s-]', '', slug).strip().lower()
        return re.sub('[-\s]+', '-', slug) or fallback