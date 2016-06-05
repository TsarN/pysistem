from pysistem import db, app, pool
from pysistem.submissions.const import *
from pysistem.users.model import User
from pysistem.compilers.model import Compiler
from pysistem.problems.model import Problem
from pysistem.checkers.model import Checker
import tempfile
import os
from pysistem.conf import DIR
from datetime import datetime

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source = db.Column(db.String(2**20))
    status = db.Column(db.Integer)
    result = db.Column(db.Integer)
    compile_log = db.Column(db.String(2**20))
    tests_passed = db.Column(db.Integer)
    submitted = db.Column(db.DateTime, default=datetime.now)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    compiler_id = db.Column(db.Integer, db.ForeignKey('compiler.id'))
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))

    def __init__(self, source=None, user=None, compiler=None, problem=None):
        self.source = source
        self.status = STATUS_CWAIT
        self.result = RESULT_UNKNOWN

        if type(user) is int:
            user = User.query.get(user)

        if type(compiler) is int:
            compiler = Compiler.query.get(compiler)

        if type(problem) is int:
            problem = Problem.query.get(problem)

        self.user = user
        self.compiler = compiler
        self.problem = problem
        self.tests_passed = 0

    def __repr__(self):
        return '<Submission #%s>' % str(self.id)

    def get_exe_path(self):
        return DIR + '/storage/submissions_bin/' + str(self.id)

    def get_source_path(self):
        return tempfile.gettempdir() + '/pysistem_submission_' + str(self.id) + '.' + self.compiler.lang

    def compile(self):
        self.status = STATUS_COMPILING
        db.session.commit()
        source_path = self.get_source_path()
        source_file = open(source_path, 'w')
        source_file.write(self.source)
        source_file.close()

        result, output = self.compiler.compile(source_path, self.get_exe_path())
        if result:
            self.status = STATUS_WAIT
        else:
            self.status = STATUS_COMPILEFAIL

        self.compile_log = output

        db.session.commit()

        os.remove(source_path)

        return result, output

    def run(self, stdin='', time_limit=1000, memory_limit=65536, commit_waiting=True):
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
        self.status = STATUS_DONE

    def get_str_result(self, color=False):
        if self.status in [STATUS_DONE, STATUS_ACT]:
            res = STR_RESULT[self.result]
            if self.result not in [RESULT_OK, RESULT_RJ]:
                res += ' (' + str(self.tests_passed + 1) + ')'
            if color:
                if self.result in [RESULT_OK] :
                    res = '<span class="text-success">' + res + '</span>'
                else:
                    res = '<span class="text-danger">' + res + '</span>'
            return res
        else:
            if self.status == STATUS_CHECKING:
                return STR_STATUS[self.status] + ' (' + str(self.tests_passed + 1) + ')'
            else:
                return STR_STATUS[self.status]

    def is_compile_failed(self):
        return self.status == STATUS_COMPILEFAIL

    def check(self):
        checker = Checker.query \
            .filter(db.and_(Checker.problem_id == self.problem_id, Checker.status == STATUS_ACT)).first()

        if checker is None:
            return -1
        else:
            return checker.check(self)

    def async_check(self):
        print("async_check()")
        pool.submit(submission_check, self.id)
        print("end async_check()")

def submission_check(id):
    if Submission.query.get(id).compile()[0]:
        Submission.query.get(id).check()