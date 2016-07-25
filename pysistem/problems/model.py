# -*- coding: utf-8 -*-

"""Problems model"""

import gzip
import io
import hashlib

import msgpack

from pysistem import db
from pysistem.submissions.const import RESULT_IE, RESULT_UNKNOWN, RESULT_OK
from pysistem.submissions.const import STATUS_ACT, STATUS_DONE, STATUS_CHECKING
from pysistem.compilers.model import Compiler

EXPORTVER = 3

class Problem(db.Model):
    """Solvable programming problem

    Fields:
    id -- unique problem identifier
    name -- problem name
    description -- problem's description, in short
    statement -- problem's statement with HTML markup
    time_limit -- maximum time problem's solutions are allowed to execute for, in milliseconds
    memory_limit -- maximum memory problem's solutions are allowed to consume, in KiB

    Relationships:
    submissions -- All user-made submissions to this problem
    test_groups -- All test groups this problem has
    checkers -- All checkers this problem has

    contests -- All contests this problem is part of (ContestProblemAssociation)
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    description = db.Column(db.String(256))
    statement = db.Column(db.Text)
    time_limit = db.Column(db.Integer)
    memory_limit = db.Column(db.Integer)

    submissions = db.relationship('Submission', cascade='all,delete',
                                  backref='problem', lazy="dynamic")
    test_groups = db.relationship('TestGroup', cascade='all,delete',
                                  backref='problem', lazy="dynamic")
    checkers = db.relationship('Checker', cascade='all,delete',
                               backref='problem', lazy="dynamic")

    contests = db.relationship('ContestProblemAssociation', lazy="dynamic",
                               back_populates='problem', cascade='all,delete')

    def __init__(self, name=None, description=None, statement=None,
                 time_limit=1000, memory_limit=65536):
        self.name = name
        self.description = description
        self.statement = statement
        self.time_limit = time_limit
        self.memory_limit = memory_limit

    def __repr__(self):
        return '<Problem %r>' % self.name

    def get_user_failed_attempts(self, user, freeze=None, subs=None):
        """(For ACM/ICPC contests): return amount of user's failed attempts before 'freeze'"""
        from pysistem.submissions.model import Submission
        subs = subs or self.submissions.filter(Submission.user_id == user.id).all()
        ans = 0
        for sub in subs:
            if freeze and sub.submitted > freeze:
                break
            if sub.status in [STATUS_DONE, STATUS_ACT]:
                if sub.result in [RESULT_OK]:
                    break
                if sub.result not in [RESULT_IE, RESULT_UNKNOWN]:
                    ans += 1
        return ans

    def user_score(self, user, freeze=None, subs=None):
        """Return Tuple: (Score for this problem, last time of last meaningful submission)"""
        from pysistem.submissions.model import Submission
        subs = subs or Submission.query.filter(db.and_(
            self.id == Submission.problem_id,
            user.id == Submission.user_id
        )).all()

        last_sub = None
        max_score = 0

        for sub in subs:
            if freeze and sub.submitted > freeze:
                break
            if sub.status in [STATUS_DONE, STATUS_ACT]:
                if sub.result not in [RESULT_IE, RESULT_UNKNOWN]:
                    last_sub = sub.submitted
                    max_score = max(max_score, sub.score)
        return max_score, last_sub

    def user_status(self, user, color=True, score=False, only_color=False):
        """Return formatted verdict string

        Arguments:
        user -- User, whose verdict needs to be returned
        color -- enable color, will return HTML markup
        score -- show score in brackets after verdict
        only_color -- will return ONLY Bootstrap color class: 'success', 'danger' etc
        """
        from pysistem.submissions.model import Submission
        subs = self.submissions.filter(Submission.user_id == user.id).all()

        attempted = None

        for sub in subs:
            if sub.status in [STATUS_DONE, STATUS_ACT]:
                if sub.result in [RESULT_OK]:
                    return sub.get_str_result(color=color, score=score, only_color=only_color)
                elif sub.result not in [RESULT_IE, RESULT_UNKNOWN]:
                    attempted = sub
            elif sub.status in [STATUS_CHECKING]:
                attempted = sub
        if attempted:
            return attempted.get_str_result(color=color, score=score, only_color=only_color)
        else:
            return ""

    def export_gzip(self):
        """Returns binary data in gzip format that accepts Problem.import_gzip"""
        to_write = msgpack.dumps({
            'name': self.name,
            'time_limit': self.time_limit,
            'memory_limit': self.memory_limit,
            'description': self.description,
            'statement': self.statement,
            'checkers': [{
                'name': checker.name,
                'compiler': checker.compiler.autodetect or checker.compiler.lang,
                'source': checker.source
            } for checker in self.checkers if checker.status in [STATUS_DONE, STATUS_ACT]],
            'test_groups': [{
                "test_pairs": [{
                    'input': test.input,
                    'pattern': test.pattern
                } for test in test_group.test_pairs],
                "score": test_group.score,
                "score_per_test": test_group.score_per_test,
                "check_all": test_group.check_all
            }               for test_group in self.test_groups],
            'version': EXPORTVER
        }, use_bin_type=True)

        out = io.BytesIO()
        with gzip.GzipFile(fileobj=out, mode='wb') as f:
            f.write(to_write)
        return out.getvalue()

    def import_gzip(self, data):
        """Update this problem using gzip-encoded 'data'"""
        try:
            from pysistem.checkers.model import Checker
            from pysistem.test_pairs.model import TestPair, TestGroup
            f = io.BytesIO()
            f.write(data)
            f.seek(0)
            input_f = gzip.GzipFile(fileobj=f, mode='rb')
            data = msgpack.load(input_f, encoding="utf-8")
            version = data.get('version', 0)
            if version not in [1, 2, 3]:
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
                    self
                )
                compiler = None
                if version in [1, 2]:
                    compiler = Compiler.query.filter(Compiler.lang == checker['lang']).first()
                else:
                    compiler = Compiler.query.filter(
                               Compiler.autodetect == checker['compiler']).first()
                    if not compiler:
                        compiler = Compiler.query.filter(
                                   Compiler.lang == checker['compiler']).first()
                if compiler:
                    c.compiler_id = compiler.id
                db.session.add(c)
                db.session.commit()
                c.compile()
            if version == 1:
                test_group = TestGroup(self)
                for test in data.get('test_pairs', ()):
                    test_pair = TestPair(
                        test['input'],
                        test['pattern']
                    )
                    test_group.test_pairs.append(test_pair)
                db.session.add(test_group)
            if version in [2, 3]:
                for tg in data.get('test_groups', ()):
                    test_group = TestGroup(self)
                    test_group.score = tg['score']
                    test_group.score_per_test = tg['score_per_test']
                    test_group.check_all = tg['check_all']
                    for test in tg['test_pairs']:
                        test_pair = TestPair(
                            test['input'],
                            test['pattern']
                        )
                        test_group.test_pairs.append(test_pair)
                    db.session.add(test_group)
            db.session.commit()
            return True
        except:
            return False

    def transliterate_name(self):
        """Transliterate this problem's name to English"""
        try:
            from transliterate import detect_language, translit
            import unicodedata
            import re
        except ImportError:
            return 'problem' + str(self.id)

        language_code = detect_language(self.name)
        trans = self.name
        if language_code:
            trans = translit(self.name, language_code, reversed=True)
        slug = unicodedata.normalize('NFKD', trans) \
                          .encode('ascii', 'ignore') \
                          .decode('ascii')
        slug = re.sub(r'[^\w\s-]', '', slug).strip().lower()
        return re.sub(r'[-\s]+', '-', slug) or ('problem' + str(self.id))

    def get_max_score(self):
        """Get problem's maximum achievable score"""
        score = 0
        try:
            for test_group in self.test_groups:
                score += test_group.score
                score += test_group.test_pairs.count() * test_group.score_per_test
        except:
            score = 0
        return score
