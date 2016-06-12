# -*- coding: utf-8 -*-
from pysistem import db
from pysistem.problems.model import Problem

from pysistem.submissions.const import *
import tempfile
import os
from subprocess import Popen, PIPE, run, STDOUT
from pysistem.conf import DIR

class Checker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    source = db.Column(db.Text)
    status = db.Column(db.Integer)
    compile_log = db.Column(db.Text)
    lang = db.Column(db.String(8))

    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'))

    def __init__(self, name='', source='', problem=None, lang='c'):
        self.name = name
        self.source = source
        self.status = STATUS_CWAIT
        self.compile_log = ''
        self.lang = lang

        if type(problem) is int:
            problem = Problem.query.get(problem)

        self.problem = problem

    def __repr__(self):
        return '<Checker %r>' % self.name

    def get_exe_path(self):
        return DIR + '/storage/checkers_bin/' + str(self.id)

    def get_ext(self):
        if self.lang == 'c++':
            return 'cpp'
        return self.lang

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

        p = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        stdout, stderr = p.communicate(input=self.source.encode())
        self.compile_log = stdout.decode()
        success = (p.returncode == 0)

        if success:
            self.status = STATUS_DONE
            self.set_act()
        else:
            self.status = STATUS_COMPILEFAIL
            db.session.commit()

        return success, stdout

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

    def check_test(self, submission, test, ntest=0):
        submission.current_test_id = test.id
        cstdout, cstderr = (b'', b'')
        db.session.commit()
        result, stdout, stderr = submission.run(test.input,
            submission.problem.time_limit, submission.problem.memory_limit,
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
            p = Popen(cmd, stdout=PIPE, stderr=STDOUT)
            cstdout, cstderr = p.communicate()
            r = p.returncode

            os.remove(input_path)
            os.remove(output_path)
            os.remove(pattern_path)

            if r == 1:
                subres = RESULT_PE
            elif r == 2:
                subres = RESULT_WA
            elif r == 3:
                subres = RESULT_IE


        submission.result = subres
        if submission.result == RESULT_OK:
            submission.score += test.test_group.score_per_test
        return cstdout.decode(), stdout.decode()

    def check(self, submission):
        from pysistem.submissions.model import SubmissionLog
        submission.result = RESULT_OK
        submission.status = STATUS_CHECKING
        submission.score = 0
        submission.check_log = ''
        ntest = 0
        last_result = RESULT_OK
        for test_group in self.problem.test_groups:
            for x in SubmissionLog.query.filter(db.and_( \
                SubmissionLog.submission_id == submission.id, \
                SubmissionLog.test_pair_id.in_([y.id for y in test_group.test_pairs]) \
                )):
                db.session.delete(x)
        db.session.commit()
        for test_group in self.problem.test_groups:
            all_passed = True
            for test in test_group.test_pairs:
                cstdout, stdout = self.check_test(submission, test, ntest)
                ntest += 1
                submission_log = SubmissionLog.query.filter(db.and_(\
                    SubmissionLog.submission_id == submission.id, \
                    SubmissionLog.test_pair_id == test.id \
                    )).first() or SubmissionLog(submission=submission, test_pair=test)
                submission_log.result = submission.result
                submission_log.log = cstdout
                submission_log.stdout = stdout
                db.session.add(submission_log)
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
        db.session.commit()
        return submission.result