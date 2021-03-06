# -*- coding: utf-8 -*-

"""Checker models"""

import tempfile
import os
from subprocess import Popen, PIPE, STDOUT

from pysistem import app, db
from pysistem.problems.model import Problem

from pysistem.submissions.const import STR_RESULT, STR_STATUS, STATUS_CWAIT
from pysistem.submissions.const import STATUS_WAIT, STATUS_COMPILEFAIL, STATUS_DONE
from pysistem.submissions.const import STATUS_ACT, STATUS_CHECKING, STATUS_COMPILING
from pysistem.submissions.const import RESULT_OK, RESULT_IE, RESULT_SV, RESULT_ML
from pysistem.submissions.const import RESULT_TL, RESULT_RE, RESULT_WA, RESULT_PE

try:
    from pysistem.conf import DIR
except: # pragma: no cover
    from pysistem.conf_default import DIR

class Checker(db.Model):
    """A submission runner

    Fields:
    id -- unique checker identifier
    name -- checker name
    source -- checker source
    status -- checker status, see pysistem.submissions.const
    compile_log -- compilation log produced by compiler

    Relationships:
    problem, problem_id -- problem, whose checker it is
    compiler, compiler_id -- compiler used to compile this checker

    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    source = db.Column(db.Text)
    status = db.Column(db.Integer)
    compile_log = db.Column(db.Text)

    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))
    compiler_id = db.Column(db.Integer, db.ForeignKey('compiler.id'))

    def __init__(self, name='', source='', problem=None):
        self.name = name
        self.source = source
        self.status = STATUS_CWAIT
        self.compile_log = ''

        if isinstance(problem, int): # pragma: no cover
            problem = Problem.query.get(problem)

        self.problem = problem

    def __repr__(self):
        return '<Checker %r>' % self.name

    def get_exe_path(self):
        """Return the pathname of checker's binary file"""
        STORAGE = app.config['STORAGE']
        return STORAGE + '/checkers_bin/' + str(self.id)

    def get_ext(self):
        """Get checker source file extension"""
        return self.compiler.lang

    def get_src_path(self):
        return DIR + '/work/work/checker_%d.%s' % (self.id, self.get_ext())

    def get_result(self):
        if self.status in [STATUS_DONE, STATUS_ACT]:
            return '<span class="text-success">%s</span>' % STR_RESULT[RESULT_OK]
        if self.status in [STATUS_COMPILEFAIL]:
            return '<span class="text-danger">%s</span>' % STR_STATUS[STATUS_COMPILEFAIL]
        return STR_STATUS[self.status] # pragma: no cover

    def compile(self):
        """Compile checker, must be called before using checker on every checking machine"""
        if self.status not in [STATUS_CWAIT, STATUS_COMPILEFAIL, STATUS_WAIT]: # pragma: no cover
            return False, b'', b''

        self.status = STATUS_COMPILING
        db.session.commit()

        with open(self.get_src_path(), "w") as file:
            file.write(self.source)

        success, stdout = self.compiler.compile(self.get_src_path(), self.get_exe_path())

        try:
            os.remove(self.get_src_path())
        except: pass

        self.compile_log = stdout

        if success:
            self.status = STATUS_DONE
            self.set_act()
        else:
            self.status = STATUS_COMPILEFAIL
            db.session.commit()

        return success, stdout

    def set_act(self):
        """Set as active checker for problem, works only if checker compiled successfully"""
        if self.status == STATUS_DONE:
            self.problem.checkers.filter(Checker.status == STATUS_ACT) \
                .update({"status": STATUS_DONE})
            self.status = STATUS_ACT
            db.session.commit()
            return True
        else:
            return False

    def check_test(self, submission, test):
        """Run submission on test. For internal use.

        Arguments:
        submission -- Submission object for checking
        test -- TestPair object for checking

        Returns:
        Tuple: (Checker output, Submission output)

        """
        submission.current_test_id = test.id
        cstdout = b''
        result, stdout, stderr = submission.run(test.input, submission.problem.time_limit,
                                                submission.problem.memory_limit,
                                                commit_waiting=False)
        subres = RESULT_OK

        if result & 8:
            subres = RESULT_IE
        elif result & 16:
            subres = RESULT_SV
        elif result & 4:
            subres = RESULT_ML
        elif result & 1:
            subres = RESULT_TL
        elif result & 2:
            subres = RESULT_RE

        if subres == RESULT_OK:

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
            proc = Popen(cmd, stdout=PIPE, stderr=STDOUT)
            cstdout, cstderr = proc.communicate()
            returncode = proc.returncode

            os.remove(input_path)
            os.remove(output_path)
            os.remove(pattern_path)

            if returncode in [0, 0xAC]:
                subres = RESULT_OK
            elif returncode in [1, 0xAB]:
                subres = RESULT_WA
            elif returncode in [2, 0xAA]:
                subres = RESULT_PE
            else:
                subres = RESULT_IE

        submission.result = subres
        if submission.result == RESULT_OK:
            submission.score += test.test_group.score_per_test
        return cstdout.decode(), stdout.decode()

    def check(self, submission, session=None):
        """(Re)check submission. For internal use.

        Arguments:
        submission -- Submission object for checking
        session -- SQLAlchemy session object to use. Default -- db.session

        Returns:
        pysistem.submissions.const -- Submission's result

        """
        print("Starting checking", submission);
        session = session or db.session
        from pysistem.submissions.model import SubmissionLog
        submission.result = RESULT_OK
        submission.status = STATUS_CHECKING
        submission.score = 0
        submission.check_log = ''
        last_result = RESULT_OK
        for submission_log in session.query(SubmissionLog).filter(
            SubmissionLog.submission_id == submission.id):
            session.remove(submission_log)

        session.commit()
        from pysistem.test_pairs.model import TestPair, TestGroup
        for test_group in session.query(TestGroup) \
            .filter(self.problem_id == TestGroup.problem_id):
            all_passed = True
            for test in session.query(TestPair) \
                .filter(test_group.id == TestPair.test_group_id):
                cstdout, stdout = self.check_test(submission, test)
                submission_log = session.query(SubmissionLog).filter(db.and_(
                    SubmissionLog.submission_id == submission.id,
                    SubmissionLog.test_pair_id == test.id
                    )).first() or SubmissionLog(submission=submission, test_pair=test)
                session.add(submission_log)
                submission_log.result = submission.result
                submission_log.log = cstdout
                submission_log.stdout = stdout
                session.commit()
                if submission.result != RESULT_OK:
                    all_passed = False
                    if last_result == RESULT_OK:
                        last_result = submission.result
                    if not test_group.check_all:
                        break
            if all_passed:
                submission.score += test_group.score
            else:
                break
        submission.current_test_id = 0
        submission.result = last_result
        submission.done()
        return submission.result
