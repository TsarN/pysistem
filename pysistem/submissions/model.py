# -*- coding: utf-8 -*-
from pysistem import db, app, cache
from pysistem.submissions.const import *
from pysistem.users.model import User
from pysistem.compilers.model import Compiler
from pysistem.problems.model import Problem
from pysistem.checkers.model import Checker
import tempfile
import os
from pysistem.conf import DIR
from datetime import datetime
from flask_babel import gettext
from time import sleep

class Submission(db.Model):
    """An attempt to solve a problem

    Fields:
    id -- unique submission identifier
    source -- submission's source code
    status -- submission's status
    result -- submission's verdict
    compile_log -- submissions's compilation log
    score -- submissions's score
    submitted -- submission datetime

    Relationships:
    user, user_id -- whose this submission is
    compiler, compiler_id -- compiler this submission is sent via
    problem, problem_id -- what problem is this submission attempting to solve
    submission_logs -- logs linked with tests in problem
    """
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.Text)
    status = db.Column(db.Integer)
    result = db.Column(db.Integer)
    compile_log = db.Column(db.Text)
    score = db.Column(db.Integer)
    submitted = db.Column(db.DateTime, default=datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    compiler_id = db.Column(db.Integer, db.ForeignKey('compiler.id'))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    submission_logs = db.relationship('SubmissionLog', cascade="all,delete", backref="submission")

    current_test_id = db.Column(db.Integer)

    def __init__(self, source=None, user=None, compiler=None, problem=None):
        self.source = source
        self.status = STATUS_CWAIT
        self.result = RESULT_UNKNOWN
        self.current_test_id = 0

        if type(user) is int:
            user = User.query.get(user)

        if type(compiler) is int:
            compiler = Compiler.query.get(compiler)

        if type(problem) is int:
            problem = Problem.query.get(problem)

        self.user = user
        self.compiler = compiler
        self.problem = problem
        self.score = 0

    def __repr__(self):
        return '<Submission #%s>' % str(self.id)

    def get_exe_path(self):
        """Get submission's executable path"""
        return DIR + '/storage/submissions_bin/' + str(self.id)

    def get_source_path(self):
        """Get submission's source path"""
        if os.path.exists('/SANDBOX'):
            return '/SANDBOX/pysistem_submission_' + str(self.id) + '.' + self.compiler.lang
        else:
            return tempfile.gettempdir() + '/pysistem_submission_' + str(self.id) + '.' + self.compiler.lang

    def compile(self):
        """Compile submission

        Returns:
        Tuple: (Success?, compiler log)
        """
        self.status = STATUS_COMPILING
        db.session.commit()
        source_path = self.get_source_path()
        source_file = open(source_path, 'w')
        source_file.write(self.source)
        source_file.close()

        try:
            os.remove(self.get_exe_path())
        except: pass

        result, output = self.compiler.compile(source_path, self.get_exe_path())
        if result:
            self.status = STATUS_WAIT
        else:
            self.status = STATUS_COMPILEFAIL

        self.compile_log = output

        db.session.commit()

        try:
            os.remove(source_path)
        except: pass

        return result, output

    def run(self, stdin='', time_limit=1000, memory_limit=65536, commit_waiting=True):
        """Run submission in sandbox

        Arguments:
        stdin -- string to pass to submission as stdin
        time_limit -- maximum execution time of program in milliseconds
        memory_limit -- maximum memory usage of program in KiB
        commit_waiting -- commit 'Waiting state' to database?

        Returns:
        Tuple: (Exit code: see runsbox(1), Program's stdout, Program's stderr: currently empty bytestring)

        """
        self.status = STATUS_CHECKING
        db.session.commit()

        source_path = self.get_source_path()
        source_file = open(source_path, 'w')
        source_file.write(self.source)
        source_file.close()

        result, stdout, stderr = self.compiler.run(self.get_exe_path(), source_path, \
            time_limit, memory_limit, stdin)

        os.remove(source_path)
        self.result = result
        if commit_waiting:  
            self.status = STATUS_WAIT
            db.session.commit()

        return result, stdout, stderr

    def done(self):
        """Set status to done"""
        self.status = STATUS_DONE

    def get_str_result(self, color=False, score=True, only_color=False, result=None, status=None):
        """Get formatted verdict string

        Arguments:
        color -- enable coloring, will produce HTML markup
        score -- show score
        only_color -- return only Bootstrap coloring class: 'sucess', 'danger' etc
        result -- overriding self.result
        status -- overriding self.status
        """
        result = result if result is not None else self.result
        status = status if status is not None else self.status
        if status in [STATUS_DONE, STATUS_ACT]:
            res = STR_RESULT[result]
            if score:
                res += ' (%d %s %d)' % (self.score, gettext('common.outof'), self.problem.get_max_score())
            if color or only_color:
                if result in [RESULT_OK] :
                    if only_color:
                        return 'success'
                    res = '<span class="text-success">' + res + '</span>'
                else:
                    if only_color:
                        return 'danger'
                    res = '<span class="text-danger">' + res + '</span>'
            return res
        else:
            res = STR_STATUS[status]
            if color or only_color:
                if only_color:
                    return 'warning'
                res = '<span class="text-warning">' + res + '</span>'
            return res

    def is_compile_failed(self):
        """Check if compilation error occurred"""
        return self.status == STATUS_COMPILEFAIL

    def check(self, session=None):
        """Start sync checking of submission"""
        session = session or db.session
        try:
            cache.delete("/submission/view/%d/%r" % (self.id, True))
            cache.delete("/submission/view/%d/%r" % (self.id, False))
        except: pass
        checker = Checker.query \
            .filter(db.and_(Checker.problem_id == self.problem_id, Checker.status == STATUS_ACT)).first()

        if checker is None:
            return -1
        self.current_test_id = 0
        return checker.check(self, session)

class SubmissionLog(db.Model):
    """A submission <-> test pair log

    Fields:
    result -- pysistem.submissions.const result
    log -- checker's log
    stdout -- submission's output

    Relationships:
    submission, submission_id -- submission
    test_pair, test_pair_id -- test_pair
    """
    result = db.Column(db.Integer)
    log = db.Column(db.Text)
    stdout = db.Column(db.Text)
    submission_id = db.Column(db.Integer, db.ForeignKey('submission.id'), primary_key=True)
    test_pair_id = db.Column(db.Integer, db.ForeignKey('test_pair.id'), primary_key=True)

    def __init__(self, result=None, log=None, stdout=None, submission=None, test_pair=None):
        self.result = result
        self.log = log
        self.stdout = stdout
        self.submission = submission
        self.test_pair = test_pair

    def __repr__(self):
        if self.submission and self.test_pair:
            return '<SubmissionLog Submission=%s TestPair=%s>' % (self.submission, self.test_pair)
        else:
            return '<SubmissionLog Unknown>'