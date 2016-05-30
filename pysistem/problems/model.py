from pysistem import db
from pysistem.submissions.const import *
import tempfile
import os
from subprocess import Popen, PIPE, run
from pysistem.conf import DIR

class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    description = db.Column(db.String(256))
    statement = db.Column(db.String)

    submissions = db.relationship('Submission', back_populates='problem')
    test_pairs = db.relationship('TestPair', back_populates='problem')
    checkers = db.relationship('Checker', back_populates='problem')

    def __init__(self, name=None, description=None, statement=None):
        self.name = name
        self.description = description
        self.statement = statement

    def __repr__(self):
        return '<Problem %r>' % self.name

class TestPair(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    input = db.Column(db.String)
    pattern = db.Column(db.String)

    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    problem = db.relationship('Problem', back_populates='test_pairs')

    def __init__(self, input='', pattern='', problem=None):
        self.input = input
        self.pattern = pattern

        if type(problem) is int:
            problem = Problem.query.get(problem)

        self.problem = problem

    def __repr__(self):
        return '<TestPair of %r>' % self.problem.name

class Checker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    source = db.Column(db.String)
    status = db.Column(db.Integer)
    compile_log_stderr = db.Column(db.String)
    compile_log_stdout = db.Column(db.String)
    lang = db.Column(db.String(8))

    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    problem = db.relationship('Problem', back_populates='checkers')

    def __init__(self, name='', source='', problem=None, lang='c'):
        self.name = name
        self.source = source
        self.status = STATUS_CWAIT
        self.compile_log_stdout = ''
        self.compile_log_stderr = ''
        self.lang = lang

        if type(problem) is int:
            problem = Problem.query.get(problem)

        self.problem = problem

    def __repr__(self):
        return '<Checker %r>' % self.name

    def get_exe_path(self):
        return DIR + '/storage/checkers_bin/' + str(self.id)

    def compile(self):
        if self.status not in [STATUS_CWAIT, STATUS_COMPILEFAIL, STATUS_WAIT]:
            return False, b'', b''

        self.status = STATUS_COMPILING
        db.session.commit()

        cmd = ''

        if self.lang == 'c':
            cmd = 'gcc -x c --std=c11 -o ' + self.get_exe_path() + ' - -lchecker -lsbox'
        if self.lang == 'c++':
            cmd = 'g++ -x c++ --std=gnu++11 -o ' + self.get_exe_path() + ' - -lchecker -lsbox'

        p = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate(input=self.source.encode())
        self.compile_log_stdout = stdout.decode()
        self.compile_log_stderr = stderr.decode()
        success = (p.returncode == 0)

        if success:
            self.status = STATUS_DONE
            self.set_act()
        else:
            self.status = STATUS_COMPILEFAIL
            db.session.commit()

        return success, stdout, stderr

    def set_act(self):
        if self.status == STATUS_DONE:
            Checker.query \
            .filter(db.and_(Checker.problem_id == self.problem_id, Checker.status == STATUS_ACT)) \
            .update({"status": STATUS_DONE})
            self.status = STATUS_ACT
            db.session.commit()
            return True
        else:
            return False

    def check(self, submission):
        submission.result = RESULT_OK
        submission.tests_passed = 0
        for test in self.problem.test_pairs:
            db.session.commit()
            result, stdout, stderr = submission.run(test.input)
            # DETERMINING RESULT
            if result & 8:
                submission.result = RESULT_IE
                break

            if result & 16:
                submission.result = RESULT_SV
                break

            if result & 4:
                submission.result = RESULT_ML
                break

            if result & 1:
                submission.result = RESULT_TL
                break

            if result & 2:
                submission.result = RESULT_RE
                break

            # NOTHING WRONG: CHECK FOR OK/WA/PE
            input_path = tempfile.gettempdir() + '/pysistem_checker_input_' + \
                         str(submission.id) + '_' + str(test.id)
            output_path = tempfile.gettempdir() + '/pysistem_checker_output_' + \
                         str(submission.id) + '_' + str(test.id)
            pattern_path = tempfile.gettempdir() + '/pysistem_checker_pattern_' + \
                         str(submission.id) + '_' + str(test.id)

            with open(input_path, 'w') as input_file, \
                 open(output_path, 'w') as output_file, \
                 open(pattern_path, 'w') as pattern_file:
                 print(test.input, file=input_file)
                 print(test.pattern, file=pattern_file)
                 print(stdout.decode(), file=output_file)

            cmd = [self.get_exe_path(), input_path, output_path, pattern_path]
            r = run(cmd).returncode

            os.remove(input_path)
            os.remove(output_path)
            os.remove(pattern_path)

            if r == 1:
                submission.result = RESULT_PE
                break

            if r == 2:
                submission.result = RESULT_WA
                break

            if r == 3:
                submission.result = RESULT_IE
                break

            submission.tests_passed += 1

        submission.done()
        db.session.commit()
        return submission.result