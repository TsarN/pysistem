# -*- coding: utf-8 -*-

import unittest
import os
from io import BytesIO
from datetime import datetime, timedelta
import warnings

from sqlalchemy import exc as sa_exc
from flask import g

from pysistem import app, db
from pysistem.users.model import User
from pysistem.compilers.model import Compiler, detect_compilers
from pysistem.contests.model import Contest, ContestProblemAssociation
from pysistem.problems.model import Problem
from pysistem.submissions.model import Submission
from pysistem.submissions.const import STATUS_ACT, STATUS_WAIT, STATUS_DONE
from pysistem.submissions.const import STATUS_COMPILEFAIL, RESULT_OK, RESULT_WA
from pysistem.submissions.const import RESULT_PE, RESULT_UNKNOWN
from pysistem.checkers.model import Checker
from pysistem.test_pairs.model import TestPair, TestGroup
from pysistem.settings.model import Setting
from pysistem.groups.model import Group, GroupUserAssociation, GroupContestAssociation
from pysistem.lessons.model import Lesson, AutoMark

try:
    from pysistem.conf import LANGUAGES
except ImportError:
    from pysistem.conf_default import LANGUAGES

class TestCase(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings("error", category=sa_exc.SAWarning)
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['SECRET_KEY'] = os.urandom(24)
        app.config['STORAGE'] = os.path.join(app.config['DIR'], 'tmp_storage')
        app.make_dirs()
        self.app = app.test_client()
        db.create_all()
        db.session.add(User(username='admin', password='admin', role='admin', email='admin@admin.com'))
        db.session.add(User(username='default', password='default', role='user', email='default@default.com'))
        db.session.commit()
        self.assertIn('en', LANGUAGES)
        with self.app.session_transaction() as session:
            session['language'] = 'en'

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_login_avail(self):
        request = self.app.get('/user/login', follow_redirects=True)
        self.assertEqual(request.status_code, 200)

    def test_signup_avail(self):
        request = self.app.get('/user/signup', follow_redirects=True)
        self.assertEqual(request.status_code, 200)

    def login(self, username, password):
        return self.app.post('/user/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.app.get('/user/logout', follow_redirects=True)

    def signup(self, username, password, password_confirm):
        return self.app.post('/user/signup', data=dict(
            username=username,
            password=password,
            passwordConfirm=password_confirm
        ), follow_redirects=True)

    def test_login_logout(self):
        request = self.login('admin', 'admin')
        self.assertIn(b'You were authorized', request.data)
        request = self.login('admin', 'admin')
        self.assertEqual(request.status_code, 403)
        request = self.logout()
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'You were logged out', request.data)
        request = self.login('notadmin', 'admin')
        self.assertIn(b'Invalid credentials', request.data)
        request = self.login('', '')
        self.assertIn(b'Invalid credentials', request.data)

    def test_signup(self):
        request = self.signup('user', 'user', 'userrendo')
        self.assertIn(b'Passwords do not match', request.data)
        request = self.signup('admin', 'user', 'user')
        self.assertIn(b'User already exists', request.data)
        request = self.signup('AdMiN', 'user', 'user')
        self.assertIn(b'User already exists', request.data)
        request = self.signup('', 'user', 'user')
        self.assertIn(b'Invalid username', request.data)
        request = self.signup('user', 'u', 'u')
        self.assertIn(b'Password is too short', request.data)
        request = self.signup('user', 'user', 'user')
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'You were registred', request.data)

    def contest_create(self, name, start, freeze, end, ruleset, unfreeze_after_end):
        return self.app.post('/contest/new', data=dict(
                name=name,
                start=start,
                freeze=freeze,
                end=end,
                ruleset=ruleset,
                unfreeze_after_end=unfreeze_after_end
            ), follow_redirects=True)

    def contest_delete(self, id):
        return self.app.get('/contest/%d/delete' % id, follow_redirects=True)

    def test_contest_create(self):
        request = self.contest_create('Denied', '2012-06-18 00:00',
            '2016-02-15 00:00', '2016-02-15 00:00', 'roi', 'on')
        self.assertEqual(request.status_code, 403)
        self.login('admin', 'admin')
        request = self.contest_create('', '2012-06-18 00:00',
            '2016-02-15 00:00', '2016-02-15 00:00', 'roi', 'on')
        self.assertIn(b'Contest name is empty', request.data)
        request = self.contest_create('Invalid', '-- 00;00',
            '2016-02-15 00:00', '2016-02-15 00:00', 'roi', 'on')
        self.assertIn(b'Invalid date/time format', request.data)
        request = self.contest_create('Hello', '2016-06-18 00:00',
            '2016-02-15 00:00', '2016-02-15 00:00', 'roi', 'on')
        self.assertIn(b'Dates are invalid', request.data)
        request = self.contest_create('Hello', '2012-06-18 00:00',
            '2016-02-15 00:00', '2016-02-15 00:00', 'acm', '')

        contest = Contest.query.filter(Contest.name == 'Hello').first()
        self.assertTrue(contest)
        self.assertEqual(contest.start, datetime(2012, 6, 18, 0, 0, 0))
        self.assertEqual(contest.freeze, datetime(2016, 2, 15, 0, 0, 0))
        self.assertEqual(contest.end, datetime(2016, 2, 15, 0, 0, 0))
        self.assertFalse(contest.unfreeze_after_end)
        self.assertEqual(contest.rules, 'acm')

    def test_contest_escape(self):
        contest = Contest(name="<'Hello'>", start=datetime(2012, 6, 18, 0, 0, 0),
            end=datetime(2016, 2, 15, 0, 0, 0), freeze=datetime(2016, 2, 15, 0, 0, 0),
            unfreeze_after_end=False, rules='acm')
        db.session.add(contest)
        db.session.commit()

        id = contest.id
        request = self.app.get('/contest/%d' % id)
        self.assertIn(b'&lt;&#39;Hello&#39;&gt;', request.data)
        self.assertNotIn(b"<'Hello'>", request.data)

    def test_contest_delete(self):
        contest = Contest(name='Hello', start=datetime(2012, 6, 18, 0, 0, 0),
            end=datetime(2016, 2, 15, 0, 0, 0), freeze=datetime(2016, 2, 15, 0, 0, 0),
            unfreeze_after_end=False, rules='acm')
        db.session.add(contest)
        db.session.commit()

        id = contest.id

        request = self.contest_delete(id)
        self.assertEqual(request.status_code, 403)
        request = self.contest_delete(9001)
        self.assertEqual(request.status_code, 404)
        self.assertTrue(Contest.query.get(id))
        self.login('admin', 'admin')
        request = self.contest_delete(id)
        self.assertFalse(Contest.query.get(id))

    def problem_create(self, name, description, statement, time_limit, memory_limit):
        return self.app.post('/problem/new', data=dict(
            name=name,
            description=description,
            statement=statement,
            time_limit=time_limit,
            memory_limit=memory_limit
        ), follow_redirects=True)

    def problem_delete(self, id):
        return self.app.get('/problem/%d/delete' % id, follow_redirects=True)

    def test_problem_create(self):
        request = self.problem_create('A+B', 'Add two numbers', 'Please do it', 1234, 54321)
        self.assertEqual(request.status_code, 403)
        self.login('admin', 'admin')
        request = self.problem_create('', 'Add two numbers', 'Please do it', 1234, 54321)
        self.assertIn(b'Problem name is empty', request.data)

        request = self.problem_create('A+B', 'Add two numbers', 'Please do it', 1234, 54321)
        problem = Problem.query.filter(Problem.name == 'A+B').first()
        self.assertTrue(problem)
        self.assertEqual(problem.name, 'A+B')
        self.assertEqual(problem.description, 'Add two numbers')
        self.assertEqual(problem.statement, 'Please do it')
        self.assertEqual(problem.time_limit, 1234)
        self.assertEqual(problem.memory_limit, 54321)

    def test_problem_delete(self):
        problem = Problem(name='A+B', description='Add two numbers',
            statement='Please do it', time_limit=1234, memory_limit=54321)
        db.session.add(problem)
        db.session.commit()
        id = problem.id

        request = self.problem_delete(id)
        self.assertEqual(request.status_code, 403)
        self.login('admin', 'admin')
        request = self.problem_delete(9001)
        self.assertEqual(request.status_code, 404)
        request = self.problem_delete(id)
        self.assertFalse(Problem.query.get(id))

    def test_problem_unicode(self):
        problem = Problem(name='Сложить А и Б', description='Сложить два числа',
            statement='Вы всё уже знаете', time_limit=1234, memory_limit=54321)
        db.session.add(problem)
        db.session.commit()
        id = problem.id

        request = self.app.get('/problem/%d' % id)
        self.assertIn('Сложить А и Б', request.data.decode())
        self.assertIn('Вы всё уже знаете', request.data.decode())

    def test_problem_import_submissions(self):
        detect_compilers()

        if not Compiler.query.filter(Compiler.lang == 'pas').first():
            self.skipTest('Pascal compiler not found')

        valid = [
            b'\x1f\x8b\x08\x00j\x08iW\x02\xff\x8d\x92]K\x14',
            b'Q\x18\xc7\xb3.\x82\x85\xfd\x0e\x0fK\xa5\xe22\xbb',
            b'k\x98\xd1n\x1bk\xee\xc2\x86\xba\xe2\x9a\x12\x19\xcb',
            b'\x99\x99\xc7uj\xde8\xe7\x8c(!\xa4\xf6\x06^',
            b'\x84\xdet\x1b\x98\xef\x11!\x1a\x82\x12\xd1}0s',
            b'\x99\x9f\xa0/\x11t\xce\xf8\x86\xbb\x93t3\xf3\x9c',
            b'\xff\xff\xf9\x9d\xe7e\xe6\xed\x06\xe3\x84\xa3\x856?',
            b'\xbc|\xcf_\xf2\xb7\xfdo\xfe\x8e\xbf\x17\xcc\x05\xb3',
            b'\xc1;\x10\xe1\xb6\xff\x05\x82\xd7\xfe\xae\xbf\x1f,\x04',
            b'\xaf x#\xccY\x7f_\xa89#_\xc8\xa5\x8c',
            b'<\xf8{2\xee\x91\xb1\x02\xfeR\xb0 \xa0\xdd\xa3',
            b'[\xfc]\xe1Jl6\x98\xf7\x0f\xfc\x83`^\xc9',
            b'\xa9\x14R\xf9x\xec\xec\x9d?\xa9\x9bK\xa9\xf9\x13',
            b'\xf9D\x13h\xd8\xd2n\xf0\xc2\xff*\xaf\x8c\xac\x0b',
            b'mi\xb8a\xf2\xec\xa9\x99<\xb3B=\x93N\xa7',
            b'3\xed\xca\xb9\xa2a\xa3Me\x1b\xda\xbf\xa8sN',
            b'T\x13A3\tcw\x13S\xe1)\x01\x1a\x9a&',
            b's\x89f\xd8\xf5\xbb\x89t\x02T\x87\xeaHe\x98',
            b"\xcfq\x1ab\xfa\x19\xa3'\x9aW \x84\x14\xd7\xf3",
            b"\xe2A#\x11\xcd\xd1Qb]'\x8d\xdc<\xed\xe8",
            b'B.\x115\xf8\xff\x16\xbb\x1dQ#\x15\x8e|\xba',
            b'\x91MnXX3\r\xcb\xe0?\xaf\xfa[:2',
            b'\x8d\x1a.7\x1c\xfb\xfb\xda$R&\x82+[\x1c',
            b'\x19\xaf\xd5\xa9\xe3\xb9l\xf1\xe5g\xa69\x14k.',
            b'\xd2\x9a\xd4[6\xb4\t\xd4\x9e\xd5\x88i\xfe\xd8\x0c',
            b'\x13]bP\xf6~n\xcd%\x9c#\xb5?\xac\x18',
            b'\xb6\xeb\xf1\xd5L<\xd6\x19\x8f5\xca\x1b\x99n\xa1',
            b'wu5;\xabB\x13\x7f@\xa3\xbc\xde\xd9u+',
            b'\xd2\xd8\x94\xbf\x8b\xb8+\xddl\xad\n=\x1dQA',
            b'h\xa2\xab\x95p\xa0K\x9f,\xb4\x1c:}\xbc\x8b',
            b'?\xbf\xd7\xc3\xb9\xc4\n\x16\xe7\xd75\xc7r\r\x13',
            b'\xe9\xf2\xb8\xab\xad2\xc7\xa3\x1a\x1e\xb6\xfcr\xa9S',
            b'\xa7\xc4\x82\xe3\xc4l<\x16\x8f=\xbfV\x18\x1c\x1c',
            b'~4X\x84\xfb\x95\x81j\xa5\xaf8#U\x8f!',
            b'\x8b\xc7\x00\xaa\xd3\xec!7L\x96\x94\x89\xe5Ro',
            b'\xb1\x04\xfd\xd5\xd1\xf2@oe\xb4:#\x13<\xfb',
            b'\x81\xa7\xd71\xd3\r\x86\r\xad\x8a2\xe6\xc9\xf4\xb1',
            b'SYq\tk\xcdJ\xba\xd8W-F"\xa9\x10',
            b'IE!\x03\xbd\xe5R\xd8\xcf$\xa1\x12%IP',
            b"\x93\xc0\xee@\xd9\xe6X\x0f'P\xb1n\xd8\xd2+",
            b'\xcb\r\rOqe\x08\x89\xde\xe7\xd8u\x91\xd3F',
            b'\xda\xb3\xe7\xbc\x01\x9c\xe2}\x86\x8d\xd9\x7f\x12j\x03',
            b'\xd1\xef1\xde\x83\xc5J)\x94+\x1e\x8f`X{',
            b'\x83y\x1e2\xc6\x81@\x07\xa8\x90\xcb\x03\x03>\x81',
            b'6\x8c\x0c\xe1S\xd4\xf8h\xa1M&\x00\x94\x1cj',
            b'\x11\xde\xd6z]\x07\x9cr\x85\x83z\x12\xc4a\xdc',
            b'\xf1l\xbd5\t\x8f\xc3\x0b\xc4\xe8O\xda\x8fj\x8d',
            b'\x144\r].b\xb4u\xe5\xa3M,\xdc!\xae',
            b'\xe91\xb5v\xfcuk\x19Ewi\xe8,\x17:',
            b'z\xfe\x02\xdaU#9\x85\x05\x00\x00']

        valid = b''.join(valid)
        invalid = b'INVALID'

        request = self.app.post('/problem/import', data=dict(
            import_file=(BytesIO(valid), 'problem.pysistem.gz')
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 403)
        self.assertFalse(Problem.query.all())
        self.login('admin', 'admin')
        request = self.app.post('/problem/import', data=dict(
            import_file=(BytesIO(valid), 'problem.pysistem.gz')
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertTrue(Problem.query.all())
        self.logout()

        problem1 = Problem.query.first()
        self.assertEqual(problem1.name, 'A+B')
        self.assertEqual(problem1.test_groups.count(), 1)
        self.assertEqual(problem1.test_groups[0].test_pairs.count(), 7)

        db.session.add(problem1)
        db.session.commit()

        problem2 = Problem()
        self.assertFalse(problem2.import_gzip(invalid))

        valid_solver_src = '''
        program aplusb;
        var
            a, b: integer;
        begin
            readln(a, b);
            writeln(a + b);
        end.
        '''

        invalid_solver_src = '''
        program aplusb;
        begin
            writeln(3);
        end.
        '''

        pe_solver_src = '''
        program aplusb;
        begin
            writeln('1 2 3');
            writeln('4 5');
        end.
        '''

        invalid_checker_src = '''
        program checker;
        begin
            writeln(stderr, 'ok')
            writeln('No semicolon: Python style!')
        end.
        '''

        submission1 = Submission(valid_solver_src,
                             user=User.query.filter(User.username == 'admin').first(),
                             compiler=Compiler.query.filter(Compiler.lang == 'pas').first(),
                             problem=problem1)

        db.session.add(submission1)
        db.session.commit()
        submission1.compile()
        self.assertEqual(submission1.status, STATUS_WAIT)
        submission1.check()
        self.assertEqual(submission1.status, STATUS_DONE)
        self.assertEqual(submission1.result, RESULT_OK)
        self.assertEqual(submission1.score, 7)

        submission2 = Submission(invalid_solver_src,
            user=User.query.filter(User.username == 'admin').first(),
            compiler=Compiler.query.filter(Compiler.lang == 'pas').first(),
            problem=problem1)

        db.session.add(submission2)
        db.session.commit()
        submission2.compile()
        self.assertEqual(submission2.status, STATUS_WAIT)
        submission2.check()
        self.assertEqual(submission2.status, STATUS_DONE)
        self.assertEqual(submission2.result, RESULT_WA)
        self.assertEqual(submission2.score, 1)

        submission4 = Submission(pe_solver_src,
            user=User.query.filter(User.username == 'admin').first(),
            compiler=Compiler.query.filter(Compiler.lang == 'pas').first(),
            problem=problem1)

        db.session.add(submission4)
        db.session.commit()
        submission4.compile()
        self.assertEqual(submission4.status, STATUS_WAIT)
        submission4.check()
        self.assertEqual(submission4.status, STATUS_DONE)
        self.assertEqual(submission4.result, RESULT_PE)
        self.assertEqual(submission4.score, 0)

        submission3 = Submission(valid_solver_src,
            user=User.query.filter(User.username == 'default').first(),
            compiler=Compiler.query.filter(Compiler.lang == 'pas').first(),
            problem=problem1)

        db.session.add(submission3)
        db.session.commit()
        submission3.compile()
        self.assertEqual(submission3.status, STATUS_WAIT)
        submission3.check()
        self.assertEqual(submission3.status, STATUS_DONE)
        self.assertEqual(submission3.result, RESULT_OK)
        self.assertEqual(submission3.score, 7)

        submission5 = Submission(invalid_checker_src,
            user=User.query.filter(User.username == 'default').first(),
            compiler=Compiler.query.filter(Compiler.lang == 'pas').first(),
            problem=problem1)

        db.session.add(submission5)
        db.session.commit()
        submission5.compile()
        self.assertEqual(submission5.status, STATUS_COMPILEFAIL)
        self.assertEqual(submission5.result, RESULT_UNKNOWN)
        self.assertEqual(submission5.score, 0)

        self.login('default', 'default')
        request = self.app.get('/problem/%d/submissions/user/admin' % problem1.id)
        self.assertEqual(request.status_code, 403)

        request = self.app.get('/problem/%d/submissions' % problem1.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Submissions of user default', request.data)
        self.assertIn(b'<td>%d</td>' % submission3.id, request.data)
        self.assertNotIn(b'<td>%d</td>' % submission1.id, request.data)
        self.assertNotIn(b'<td>%d</td>' % submission2.id, request.data)
        self.assertNotIn(b'<td>%d</td>' % submission4.id, request.data)

        requestx = self.app.get('/problem/%d/submissions/user/default' % problem1.id)
        self.assertEqual(requestx.status_code, 200)
        self.assertEqual(requestx.data, request.data)

        self.logout()
        self.login('admin', 'admin')
        request = self.app.get('/problem/%d/submissions/user/default' % problem1.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Submissions of user default', request.data)
        self.assertIn(b'<td>%d</td>' % submission3.id, request.data)
        self.assertNotIn(b'<td>%d</td>' % submission1.id, request.data)
        self.assertNotIn(b'<td>%d</td>' % submission2.id, request.data)
        self.assertNotIn(b'<td>%d</td>' % submission4.id, request.data)

        request = self.app.get('/problem/%d/submissions/user/admin' % problem1.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Submissions of user admin', request.data)
        self.assertNotIn(b'<td>%d</td>' % submission3.id, request.data)
        self.assertIn(b'<td>%d</td>' % submission1.id, request.data)
        self.assertIn(b'<td>%d</td>' % submission2.id, request.data)
        self.assertIn(b'<td>%d</td>' % submission4.id, request.data)

        request = self.app.get('/problem/%d/submissions' % problem1.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Submissions of user admin', request.data)
        self.assertNotIn(b'<td>%d</td>' % submission3.id, request.data)
        self.assertIn(b'<td>%d</td>' % submission1.id, request.data)
        self.assertIn(b'<td>%d</td>' % submission2.id, request.data)
        self.assertIn(b'<td>%d</td>' % submission4.id, request.data)

        request = self.app.get('/problem/%d/checkers' % problem1.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'<span class="text-success">Accepted</span>', request.data)
        self.assertNotIn(b'<span class="text-danger">Compilation Error</span>', request.data)
        self.assertNotIn(b'View compilation log', request.data)

        checker2 = Checker(name='Invalid checker', source=invalid_checker_src, problem=problem1)
        checker2.compiler = Compiler.query.filter(Compiler.lang == 'pas').first()
        db.session.add(checker2)
        db.session.commit()
        checker2.compile()

        request = self.app.get('/problem/%d/checkers' % problem1.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'<span class="text-success">Accepted</span>', request.data)
        self.assertIn(b'<span class="text-danger">Compilation Error</span>', request.data)
        self.assertIn(b'View compilation log', request.data)
        self.assertIn(b'Invalid checker', request.data)

        request = self.app.get('/submission/%d' % submission1.id)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/submission/%d/source' % submission1.id)
        self.assertEqual(request.status_code, 200)
        self.assertEqual(request.data.decode(), submission1.source)
        request = self.app.get('/submission/%d/compilelog' % submission1.id)
        self.assertEqual(request.status_code, 200)
        self.assertEqual(request.data, submission1.compile_log)
        user = User.query.filter(User.username == 'admin').first()
        self.assertTrue(user)
        user.role = 'user'
        db.session.add(user)
        db.session.commit()
        request = self.app.get('/')
        self.assertNotIn(b'Server settings', request.data)
        request = self.app.get('/submission/%d/compilelog' % submission1.id)
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/submission/%d/source' % submission1.id)
        self.assertEqual(request.status_code, 200)
        self.assertEqual(request.data.decode(), submission1.source)
        user.role == 'admin'
        db.session.commit()
        self.logout()
        request = self.app.get('/submission/%d/compilelog' % submission1.id)
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/submission/%d/source' % submission1.id)
        self.assertEqual(request.status_code, 403)

        self.login('admin', 'admin')
        request = self.app.get('/submission/9001/compilelog')
        self.assertEqual(request.status_code, 404)
        request = self.app.get('/submission/9001/source')
        self.assertEqual(request.status_code, 404)

    def test_checker_actions(self):
        detect_compilers()
        self.assertTrue(Compiler.query.count())
        problem = Problem(name='A+B', description='Add two numbers',
            statement='Please do it', time_limit=1234, memory_limit=54321)
        db.session.add(problem)
        checker = Checker('Test checker', '', problem)
        checker.compiler = Compiler.query.first()
        db.session.add(checker)
        db.session.commit()

        self.assertTrue(checker)
        request = self.app.get('/problem/actchecker/%d' % checker.id)
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/problem/delchecker/%d' % checker.id)
        self.assertEqual(request.status_code, 403)

        request = self.app.get('/problem/actchecker/9001')
        self.assertEqual(request.status_code, 404)
        request = self.app.get('/problem/delchecker/9001')
        self.assertEqual(request.status_code, 404)

        self.login('admin', 'admin')
        request = self.app.get('/problem/actchecker/%d' % checker.id)
        self.assertNotEqual(checker.status, STATUS_ACT)

        checker = Checker('Another checker', '', problem)
        checker.compiler = Compiler.query.first()
        checker.status = STATUS_DONE
        db.session.add(checker)
        db.session.commit()
        id = checker.id

        request = self.app.get('/problem/actchecker/%d' % checker.id)
        checker = Checker.query.get(id)
        self.assertTrue(checker)
        self.assertEqual(checker.status, STATUS_ACT)

        request = self.app.get('/problem/delchecker/%d' % id)
        self.assertFalse(Checker.query.get(id))

    def create_test_group(self, problem_id, score, score_per_test, check_all):
        return self.app.post('/problem/%d/testgroup/new' % problem_id, data=dict(
            score=score,
            score_per_test=score_per_test,
            check_all=check_all
        ), follow_redirects=True)

    def test_problem_pages(self):
        problem = Problem(name='Сложить А и Б', description='Сложить два числа',
            statement='Вы всё уже знаете', time_limit=1234, memory_limit=54321)
        db.session.add(problem)
        db.session.commit()

        request = self.app.get('/problem/%d' % problem.id)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/problem/%d/submissions' % problem.id, follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Please log in to view this page', request.data)
        request = self.app.get('/problem/%d/checkers' % problem.id)
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/problem/%d/tests' % problem.id)
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/problem/%d/export' % problem.id)
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/problem/%d/delete' % problem.id)
        self.assertEqual(request.status_code, 403)

        self.login('default', 'default')
        request = self.app.get('/problem/%d' % problem.id)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/problem/%d/submissions' % problem.id, follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertNotIn(b'Please log in to view this page', request.data)
        request = self.app.get('/problem/%d/checkers' % problem.id)
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/problem/%d/tests' % problem.id)
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/problem/%d/export' % problem.id)
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/problem/%d/delete' % problem.id)
        self.assertEqual(request.status_code, 403)

        self.logout()
        self.login('admin', 'admin')
        request = self.app.get('/problem/%d' % problem.id)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/problem/%d/submissions' % problem.id, follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertNotIn(b'Please log in to view this page', request.data)
        request = self.app.get('/problem/%d/checkers' % problem.id)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/problem/%d/tests' % problem.id)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/problem/%d/export' % problem.id)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/problem/%d/delete' % problem.id, follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertFalse(Problem.query.filter(Problem.name == 'A+B').first())

    def test_testpair_actions(self):
        problem = Problem(name='A+B', description='Add two numbers',
            statement='Please do it', time_limit=1234, memory_limit=54321)
        db.session.add(problem)
        db.session.commit()

        self.assertFalse(TestGroup.query.filter(TestGroup.problem_id == problem.id).all())
        request = self.create_test_group(problem.id, 42, '13', 'on')
        self.assertEqual(request.status_code, 403)
        self.login('admin', 'admin')
        request = self.create_test_group(9001, 42, 13, 'on')
        self.assertEqual(request.status_code, 404)
        request = self.create_test_group(problem.id, '42', 13, 'on')
        self.assertEqual(request.status_code, 200)
        self.assertEqual(TestGroup.query.filter(TestGroup.problem_id == problem.id).count(), 1)

        test_group = TestGroup.query.filter(TestGroup.problem_id == problem.id).first()
        self.assertFalse(test_group.test_pairs.count())
        self.assertEqual(test_group.score, 42)
        self.assertEqual(test_group.score_per_test, 13)
        self.assertTrue(test_group.check_all)

        # Testing ZIP uploads
        zip1 = b''.join([b'PK\x03\x04\x14\x00\x00\x00\x00\x00xx\xd5HX',
                         b'\xad\xfa\xf2\x03\x00\x00\x00\x03\x00\x00\x00\x0b\x00\x00\x00',
                         b'input01.txt2 3P',
                         b'K\x03\x04\x14\x00\x00\x00\x00\x00|x\xd5HRO',
                         b'\xdf\x87\x03\x00\x00\x00\x03\x00\x00\x00\x0b\x00\x00\x00i',
                         b'nput02.txt5 6PK',
                         b'\x01\x02\x14\x03\x14\x00\x00\x00\x00\x00xx\xd5HX',
                         b'\xad\xfa\xf2\x03\x00\x00\x00\x03\x00\x00\x00\x0b\x00\x00\x00',
                         b'\x00\x00\x00\x00\x00\x00\x00\x00\x80\x01\x00\x00\x00\x00i',
                         b'nput01.txtPK\x01\x02\x14',
                         b'\x03\x14\x00\x00\x00\x00\x00|x\xd5HRO\xdf\x87',
                         b'\x03\x00\x00\x00\x03\x00\x00\x00\x0b\x00\x00\x00\x00\x00\x00',
                         b'\x00\x00\x00\x00\x00\x80\x01,\x00\x00\x00inpu',
                         b't02.txtPK\x05\x06\x00\x00\x00\x00',
                         b'\x02\x00\x02\x00r\x00\x00\x00X\x00\x00\x00\x00\x00'])

        zip2 = b''.join([b'PK\x03\x04\x14\x00\x00\x00\x00\x00\xa6x\xd5HX',
                         b'\xad\xfa\xf2\x03\x00\x00\x00\x03\x00\x00\x00\x0b\x00\x00\x00',
                         b'input01.txt2 3P',
                         b'K\x03\x04\x14\x00\x00\x00\x00\x00\xa7x\xd5HRO',
                         b'\xdf\x87\x03\x00\x00\x00\x03\x00\x00\x00\x0b\x00\x00\x00i',
                         b'nput02.txt5 6PK',
                         b'\x03\x04\x14\x00\x00\x00\x00\x00\xa8x\xd5H\xae+\xb1',
                         b'\x84\x01\x00\x00\x00\x01\x00\x00\x00\r\x00\x00\x00pa',
                         b'ttern01.txt5PK\x03',
                         b'\x04\x14\x00\x00\x00\x00\x00\xaax\xd5Hw\x15Z\xd6',
                         b'\x02\x00\x00\x00\x02\x00\x00\x00\r\x00\x00\x00pat',
                         b'tern02.txt11PK\x01',
                         b'\x02\x14\x03\x14\x00\x00\x00\x00\x00\xa6x\xd5HX\xad',
                         b'\xfa\xf2\x03\x00\x00\x00\x03\x00\x00\x00\x0b\x00\x00\x00\x00',
                         b'\x00\x00\x00\x00\x00\x00\x00\x80\x01\x00\x00\x00\x00in',
                         b'put01.txtPK\x01\x02\x14\x03',
                         b'\x14\x00\x00\x00\x00\x00\xa7x\xd5HRO\xdf\x87\x03',
                         b'\x00\x00\x00\x03\x00\x00\x00\x0b\x00\x00\x00\x00\x00\x00\x00',
                         b'\x00\x00\x00\x00\x80\x01,\x00\x00\x00input',
                         b'02.txtPK\x01\x02\x14\x03\x14\x00\x00',
                         b'\x00\x00\x00\xa8x\xd5H\xae+\xb1\x84\x01\x00\x00\x00',
                         b'\x01\x00\x00\x00\r\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                         b'\x00\x80\x01X\x00\x00\x00pattern0',
                         b'1.txtPK\x01\x02\x14\x03\x14\x00\x00\x00',
                         b'\x00\x00\xaax\xd5Hw\x15Z\xd6\x02\x00\x00\x00\x02',
                         b'\x00\x00\x00\r\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                         b'\x80\x01\x84\x00\x00\x00pattern02',
                         b'.txtPK\x05\x06\x00\x00\x00\x00\x04\x00\x04',
                         b'\x00\xe8\x00\x00\x00\xb1\x00\x00\x00\x00\x00'])
        
        zip3 = b'INVALID'

        self.logout()
        request = self.app.post('/problem/addtestzip/%d' % test_group.id, data=dict(
            zip_file=(BytesIO(zip1), 'zip1.zip')
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 403)

        self.login('admin', 'admin')
        request = self.app.post('/problem/addtestzip/%d' % test_group.id, data=dict(
            zip_file=(BytesIO(zip1), 'zip1.zip')
        ), follow_redirects=True)

        test_pairs = test_group.test_pairs
        self.assertEqual(test_pairs.count(), 2)
        self.assertIn(b'Tests added from ZIP file', request.data)
        self.assertEqual(test_pairs[0].input, '2 3')
        self.assertEqual(test_pairs[1].input, '5 6')
        self.assertEqual(test_pairs[0].pattern, '')
        self.assertEqual(test_pairs[1].pattern, '')

        request = self.app.post('/problem/addtestzip/%d' % test_group.id, data=dict(
            zip_file=(BytesIO(zip2), 'zip2.zip')
        ), follow_redirects=True)

        db.session.expire(test_group)
        test_pairs = test_group.test_pairs
        self.assertEqual(test_pairs.count(), 4)
        self.assertIn(b'Tests added from ZIP file', request.data)
        self.assertEqual(test_pairs[0].input, '2 3')
        self.assertEqual(test_pairs[1].input, '5 6')
        self.assertEqual(test_pairs[2].input, '2 3')
        self.assertEqual(test_pairs[3].input, '5 6')
        self.assertEqual(test_pairs[0].pattern, '')
        self.assertEqual(test_pairs[1].pattern, '')
        self.assertEqual(test_pairs[2].pattern, '5')
        self.assertEqual(test_pairs[3].pattern, '11')

        request = self.app.post('/problem/addtestzip/%d' % test_group.id, data=dict(
            zip_file=(BytesIO(zip3), 'zip3.zip')
        ), follow_redirects=True)
        db.session.expire(test_group)
        test_pairs = test_group.test_pairs
        self.assertEqual(test_pairs.count(), 4)
        self.assertIn(b'ZIP file is corrupted', request.data)

        request = self.app.post('/problem/addtestzip/%d' % test_group.id, follow_redirects=True)
        self.assertIn(b'No ZIP file', request.data)

        self.logout()
        request = self.app.post('/problem/addtest/%d' % test_group.id, data=dict(
            input_file=(BytesIO(b'-3 -4'), "input.txt")
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 403)

        request = self.app.post('/problem/deltest/%d' % test_pairs[2].id, follow_redirects=True)
        self.assertEqual(request.status_code, 403)

        self.login('admin', 'admin')
        request = self.app.post('/problem/addtest/%d' % test_group.id, data=dict(
            input_file=(BytesIO(b'-3 -4'), "input.txt")
        ), follow_redirects=True)
        db.session.expire(test_group)
        test_pairs = test_group.test_pairs
        self.assertEqual(test_pairs.count(), 5)
        self.assertEqual(test_pairs[4].input, '-3 -4')
        self.assertEqual(test_pairs[4].pattern, '')

        request = self.app.post('/problem/deltest/9001', follow_redirects=True)
        self.assertEqual(request.status_code, 404)

        request = self.app.post('/problem/deltest/%d' % test_pairs[2].id, follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        db.session.expire(test_group)
        test_pairs = test_group.test_pairs
        self.assertEqual(test_pairs.count(), 4)
        self.assertEqual(test_pairs[0].input, '2 3')
        self.assertEqual(test_pairs[1].input, '5 6')
        self.assertEqual(test_pairs[2].input, '5 6')
        self.assertEqual(test_pairs[3].input, '-3 -4')
        self.assertEqual(test_pairs[0].pattern, '')
        self.assertEqual(test_pairs[1].pattern, '')
        self.assertEqual(test_pairs[2].pattern, '11')
        self.assertEqual(test_pairs[3].pattern, '')

        for test_pair in test_pairs:
            request = self.app.get('/testpair/%d/input' % test_pair.id)
            self.assertEqual(request.status_code, 200)
            self.assertEqual(request.data.decode(), test_pair.input)
            request = self.app.get('/testpair/%d/pattern' % test_pair.id)
            self.assertEqual(request.status_code, 200)
            self.assertEqual(request.data.decode(), test_pair.pattern)

        self.logout()

        for test_pair in test_pairs:
            request = self.app.get('/testpair/%d/input' % test_pair.id)
            self.assertEqual(request.status_code, 403)
            self.assertNotEqual(request.data.decode(), test_pair.input)
            request = self.app.get('/testpair/%d/pattern' % test_pair.id)
            self.assertEqual(request.status_code, 403)
            self.assertNotEqual(request.data.decode(), test_pair.pattern)

        request = self.app.post('/problem/deltestgroup/%d' % test_group.id, follow_redirects=True)
        self.assertEqual(request.status_code, 403)

        request = self.app.post('/problem/deltestgroup/9001')
        self.assertEqual(request.status_code, 404)

        self.login('admin', 'admin')
        id = test_group.id
        request = self.app.post('/problem/deltestgroup/%d' % test_group.id, follow_redirects=True)
        self.assertFalse(TestGroup.query.get(id))

    def test_compilers_available(self):
        detect_compilers()
        self.assertTrue(Compiler.query.all())
        for compiler in Compiler.query:
            self.assertTrue(compiler.is_available())

    def test_profile(self):
        request = self.app.get('/user', follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Please log in to view this page', request.data)
        request = self.app.get('/user/admin', follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Please log in to view this page', request.data)

        self.login('default', 'default')
        request = self.app.get('/user/greatintellegence/edit', follow_redirects=True)
        self.assertEqual(request.status_code, 404)
        request = self.app.get('/user', follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Change password', request.data)
        self.assertNotIn(b'Hidden', request.data)
        requestx = self.app.get('/user/default')
        self.assertEqual(requestx.status_code, 200)
        self.assertEqual(request.data, requestx.data)
        del requestx

        request = self.app.get('/user/admin')
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Hidden', request.data)
        self.assertNotIn(b'admin@admin.com', request.data)
        self.assertNotIn(b'Change password', request.data)

    def test_problem_contest_relations(self):
        problem1 = Problem(name='A+B', description='Add two numbers',
            statement='Just do it', time_limit=1234, memory_limit=54321)
        db.session.add(problem1)
        problem2 = Problem(name='1 to N', description='List all integers from 1 to N',
            statement='Please do it. Again.', time_limit=1234, memory_limit=54321)
        db.session.add(problem2)

        now_plus_10m = datetime.now() + timedelta(minutes = 10)

        contest = Contest(name="<'Hello'>", start=now_plus_10m,
            end=now_plus_10m, freeze=now_plus_10m,
            unfreeze_after_end=False, rules='acm')
        db.session.add(contest)
        db.session.commit()

        request = self.app.get('/problem/%d' % problem1.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Just do it', request.data)
        request = self.app.get('/problem/%d' % problem2.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Please do it. Again.', request.data)

        request = self.app.get('/contest/%d/linkwith/%d' % (contest.id, problem1.id))
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/problem/%d' % problem1.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Just do it', request.data)

        self.login('admin', 'admin')
        request = self.app.get('/contest/%d/linkwith/%d' % (contest.id, problem1.id), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/problem/%d' % problem1.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Just do it', request.data)

        self.logout()
        request = self.app.get('/problem/%d' % problem1.id)
        self.assertEqual(request.status_code, 403)
        self.assertNotIn(b'Just do it', request.data)
        request = self.app.get('/contest/%d/unlinkwith/%d' % (contest.id, problem1.id))
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/problem/%d' % problem1.id)
        self.assertEqual(request.status_code, 403)
        self.assertNotIn(b'Just do it', request.data)
        self.login('admin', 'admin')
        request = self.app.get('/contest/%d/unlinkwith/%d' % (contest.id, problem1.id), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.logout()
        request = self.app.get('/problem/%d' % problem1.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Just do it', request.data)

        request = self.app.get('/contest/%d/problemprefix/%d' % (contest.id, problem1.id),
            data=dict(prefix='A'), follow_redirects=True)
        self.assertEqual(request.status_code, 403)

        self.login('admin', 'admin')
        request = self.app.get('/contest/%d/problemprefix/%d' % (contest.id, problem1.id),
            data=dict(prefix='A'), follow_redirects=True)
        self.assertEqual(request.status_code, 404)

        request = self.app.get('/contest/%d/linkwith/%d' % (contest.id, problem1.id), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/contest/%d/linkwith/%d' % (contest.id, problem2.id), follow_redirects=True)
        self.assertEqual(request.status_code, 200)

        request = self.app.get('/contest/%d/problemprefix/%d' % (contest.id, problem1.id),
            data=dict(prefix='A'), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/contest/%d/problemprefix/%d' % (contest.id, problem2.id),
            data=dict(prefix='B'), follow_redirects=True)
        self.assertEqual(request.status_code, 200)

        request = self.app.get('/contest/%d' % contest.id)
        self.assertIn(b'A+B', request.data)
        self.assertIn(b'1 to N', request.data)

        self.assertLess(request.data.find(b'A+B'), request.data.find(b'1 to N'))

        request = self.app.get('/contest/%d/problemprefix/%d' % (contest.id, problem1.id),
            data=dict(prefix='B'), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/contest/%d/problemprefix/%d' % (contest.id, problem2.id),
            data=dict(prefix='A'), follow_redirects=True)
        self.assertEqual(request.status_code, 200)

        request = self.app.get('/contest/%d' % contest.id)
        self.assertIn(b'A+B', request.data)
        self.assertIn(b'1 to N', request.data)

        self.assertGreater(request.data.find(b'A+B'), request.data.find(b'1 to N'))

    def test_settings(self):
        request = self.app.get('/settings', follow_redirects=True)
        self.assertEqual(request.status_code, 403)
        self.login('admin', 'admin')

        self.assertTrue(Setting.get('allow_guest_view'))
        self.assertTrue(Setting.get('allow_signup'))
        self.assertEqual(Setting.get('scoreboard_cache_timeout'), 60)

        request = self.app.post('/settings/', data=dict(
            allow_guest_view="",
            allow_signup="checked",
            scoreboard_cache_timeout=42
        ), follow_redirects=True)

        self.assertEqual(request.status_code, 200)
        self.assertIn(b'42', request.data)

        request = self.app.post('/settings/', data=dict(
            allow_guest_view="",
            allow_signup="",
            scoreboard_cache_timeout=34,
        ), follow_redirects=True)

        self.assertEqual(request.status_code, 200)
        self.assertNotIn(b'Invalid username regex', request.data)
        db.session.commit()
        self.assertFalse(Setting.get('allow_guest_view'))
        self.assertFalse(Setting.get('allow_signup'))
        self.assertEqual(Setting.get('scoreboard_cache_timeout'), 34)

        self.logout()
        request = self.app.get('/')
        self.assertNotIn(b'Anonymous', request.data)

    def test_groups(self):
        request = self.app.post('/group/create', data=dict(
            name="groupname"
        ))
        self.assertEqual(request.status_code, 403)
        self.login('admin', 'admin')
        request = self.app.post('/group/create', data=dict(
            name="groupname"
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 200)

        request = self.app.post('/group/create', data=dict(
            name=""
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Group name is empty', request.data)

        group = Group.query.filter(Group.name == 'groupname').first()
        self.assertTrue(group)
        self.assertEqual(group.name, 'groupname')
        self.logout()

        request = self.app.post('/group/%d/rename' % group.id, data=dict(
            name="newname"
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 403)
        db.session.expire(group)
        self.assertEqual(group.name, 'groupname')

        self.login('admin', 'admin')
        request = self.app.post('/group/%d/rename' % group.id, data=dict(
            name="newname"
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        db.session.expire(group)
        self.assertEqual(group.name, 'newname')

        request = self.app.post('/group/%d/rename' % group.id, data=dict(
            name=""
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Group name is empty', request.data)

    def test_group_permissions(self):
        group = Group(name='groupname')
        db.session.add(group)
        teacher = User(username='teacher', password='teacher', role='user')
        db.session.add(teacher)
        db.session.commit()

        assoc = GroupUserAssociation(role='admin')
        assoc.group_id = group.id
        assoc.user_id = teacher.id
        db.session.add(assoc)
        db.session.commit()

        request = self.app.get('/contest/new')
        self.assertEqual(request.status_code, 403)
        request = self.app.get('/contest/new?group_id=%d' % group.id)
        self.assertEqual(request.status_code, 403)
        self.login('teacher', 'teacher')
        request = self.app.get('/contest/new?group_id=%d' % group.id)
        self.assertEqual(request.status_code, 200)
        request = self.app.post('/contest/new', data=dict(
                name='TestContest',
                start='2012-06-18 00:00',
                freeze='2016-02-15 00:00',
                end='2016-02-15 00:00',
                ruleset='roi',
                unfreeze_after_end=True,
                group_id=group.id
            ), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        db.session.expire(group)
        self.assertTrue(group.contests.count())
        self.assertEqual(group.contests[0].name, 'TestContest')
        self.assertTrue(teacher.is_admin(contest=group.contests[0]))

        problem = Problem(name='A+B', description='Add two numbers',
            statement='Just do it', time_limit=1234, memory_limit=54321)
        db.session.add(problem)
        db.session.commit()

        self.assertFalse(teacher.is_admin(problem=problem))

        assoc = ContestProblemAssociation(prefix='A')
        assoc.problem_id = problem.id
        assoc.contest_id = group.contests[0].contest.id
        db.session.add(assoc)
        db.session.commit()

        self.assertTrue(teacher.is_admin(problem=problem))

        request = self.app.post('/user/default/edit', data={
                ("group-%d" % group.id): "user"
            }, follow_redirects=True)
        self.assertEqual(request.status_code, 403)
        self.logout()
        self.login('default', 'default')
        request = self.app.get('/group/%d/contests' % group.id, follow_redirects=True)
        self.assertEqual(request.status_code, 403)
        self.logout()
        request = self.app.get('/group/%d/contests' % group.id, follow_redirects=True)
        self.assertEqual(request.status_code, 403)
        self.login('admin', 'admin')
        request = self.app.get('/group/%d/contests' % group.id, follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        request = self.app.get('/group/9001/contests', follow_redirects=True)
        self.assertEqual(request.status_code, 404)
        self.logout()
        user = User.query.filter(User.username == 'default').first()
        request = self.app.post('/user/default/edit', data={
                ("group-%d" % group.id): "user",
                "first_name": "Sir",
                "last_name": "Userrendo",
                "email": "youdontknowme@example.com"
            }, follow_redirects=True)
        self.assertEqual(request.status_code, 403)
        self.assertTrue(user)
        db.session.expire(user)
        db.session.expire(group)
        self.assertNotEqual(user.first_name, "Sir")
        self.assertNotEqual(user.last_name, "Userrendo")
        self.assertNotEqual(user.email, "youdontknowme@example.com")
        self.assertNotIn(user, [i.user for i in group.users])

        self.login('default', 'default')
        request = self.app.post('/user/default/edit', data={
                ("group-%d" % group.id): "user",
                "first_name": "Dog",
                "last_name": "Memes",
                "email": "again@example.com"
            }, follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertTrue(user)
        db.session.expire(user)
        db.session.expire(group)
        self.assertEqual(user.first_name, "Dog")
        self.assertEqual(user.last_name, "Memes")
        self.assertEqual(user.email, "again@example.com")
        self.assertNotIn(user, [i.user for i in group.users])
        self.logout()

        self.login('admin', 'admin')
        request = self.app.post('/user/default/edit', data={
                ("group-%d" % group.id): "user",
                "first_name": "Sir",
                "last_name": "Userrendo",
                "email": "youdontknowme@example.com"
            }, follow_redirects=True)
        db.session.expire(user)
        db.session.expire(group)
        self.assertEqual(request.status_code, 200)
        self.assertTrue(user)
        self.assertEqual(user.first_name, "Sir")
        self.assertEqual(user.last_name, "Userrendo")
        self.assertEqual(user.email, "youdontknowme@example.com")
        self.assertIn(user, [i.user for i in group.users])
        self.logout()
        self.login('default', 'default')
        request = self.app.get('/group/%d/contests' % group.id, follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertTrue(teacher.is_admin(user=user))
        self.assertFalse(user.is_admin(user=teacher))
        self.assertFalse(user.is_admin(user=user))

    @unittest.skipUnless('ru' in LANGUAGES and 'en' in LANGUAGES,
                         "Russian and English locales required")
    def test_locale_change(self):
        request = self.app.get('/')
        with self.app.session_transaction() as session:
            self.assertEqual(session['language'], 'en')
        self.assertIn('Anonymous', request.data.decode())

        request = self.app.get('/locale/set/en', follow_redirects=True)
        with self.app.session_transaction() as session:
            self.assertEqual(session['language'], 'en')
        self.assertIn('Anonymous', request.data.decode())

        request = self.app.get('/locale/set/ru', follow_redirects=True)
        with self.app.session_transaction() as session:
            self.assertEqual(session['language'], 'ru')
        self.assertIn('Гость', request.data.decode())

        request = self.app.get('/locale/set/nosuchlanguage', follow_redirects=True)
        with self.app.session_transaction() as session:
            self.assertEqual(session['language'], 'ru')
        self.assertIn('Гость', request.data.decode())

    def test_lessons(self):
        group = Group(name='groupname')
        db.session.add(group)
        teacher = User(username='teacher', password='teacher', role='user')
        db.session.add(teacher)
        db.session.commit()
        user = User.query.filter(User.username == 'default').first()
        assoc = GroupUserAssociation(role='admin')
        assoc.group_id = group.id
        assoc.user_id = teacher.id
        db.session.add(assoc)
        assoc = GroupUserAssociation(role='user')
        assoc.group_id = group.id
        assoc.user_id = user.id
        db.session.add(assoc)
        db.session.commit()

        request = self.app.get('/lesson/%d/new' % group.id)
        self.assertEqual(request.status_code, 403)
        request = self.app.post('/lesson/%d/new' % group.id, data=dict(
            name='Introduction',
            start='2016-06-23 12:57',
            end='2016-06-23 12:58'
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 403)

        self.login('teacher', 'teacher')
        request = self.app.get('/lesson/%d/new' % group.id)
        self.assertEqual(request.status_code, 200)
        request = self.app.post('/lesson/%d/new' % group.id, data=dict(
            name='',
            start='2016-06-23 12:57',
            end='2016-06-23 12:58'
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Empty lesson name', request.data)
        request = self.app.post('/lesson/%d/new' % group.id, data=dict(
            name='Introduction',
            start='++ 12;57',
            end='2016-06-23 12:58'
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Invalid date/time format', request.data)
        request = self.app.post('/lesson/%d/new' % group.id, data=dict(
            name='Introduction',
            start='2016-06-23 12:57',
            end='2016-06-23 12:58'
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        db.session.expire(group)
        self.assertEqual(group.lessons.count(), 1)
        self.assertEqual(group.lessons[0].name, 'Introduction')

        request = self.app.get('/group/%d/lessons' % group.id)
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Introduction', request.data)

        lesson = Lesson.query.filter(Lesson.name == 'Introduction').first()
        self.assertTrue(lesson)

        request = self.app.post('/lesson/%d/edit' % lesson.id, data=dict(
            name='Maximum',
            contest_id=1
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 404)
        contest = Contest(name="Test contest", start=datetime.now(), end=datetime.now(), freeze=datetime.now())
        db.session.add(contest)
        db.session.commit()
        request = self.app.post('/lesson/%d/edit' % lesson.id, data=dict(
            name='Maximum',
            contest_id=contest.id,
            start='2016-06-23 12:57',
            end='2016-06-23 12:58'
        ), follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        db.session.expire(lesson)
        self.assertEqual(lesson.name, 'Maximum')
        self.assertEqual(lesson.start, datetime(2016, 6, 23, 12, 57))
        self.assertEqual(lesson.end, datetime(2016, 6, 23, 12, 58))

        self.logout()
        request = self.app.post('/lesson/%d/edit' % lesson.id, data={
            "name": 'Maximum',
            "contest_id": contest.id,
            "start": '2016-06-23 12:57',
            "end": '2016-06-23 12:58',
            "user-mark-%d" % user.id: "4+",
            "user-was-%d" % user.id: "on",
            "am-newscore1-required": 50,
            "am-newscore1-mark": "5-",
            "am-newscore1-points": 3,
            "am-newscore1-avail": "on"
        }, follow_redirects=True)
        db.session.expire(lesson)
        self.assertEqual(request.status_code, 403)

        self.login('teacher', 'teacher')
        request = self.app.post('/lesson/%d/edit' % lesson.id, data={
            "name": 'Maximum',
            "contest_id": contest.id,
            "start": '2016-06-23 12:57',
            "end": '2016-06-23 12:58',
            "user-mark-%d" % user.id: "4+",
            "user-was-%d" % user.id: "on",
            "am-newscore1-required": 50,
            "am-newscore1-mark": "5-",
            "am-newscore1-points": 3,
            "am-newscore1-avail": "on"
        }, follow_redirects=True)
        db.session.expire(lesson)
        self.assertEqual(request.status_code, 200)
        self.assertEqual(lesson.auto_marks.count(), 1)
        self.assertEqual(lesson.auto_marks[0].mark, "5-")
        self.assertEqual(lesson.auto_marks[0].required, 50)
        self.assertEqual(lesson.auto_marks[0].points, 3)
        self.assertEqual(request.status_code, 200)
        self.assertEqual(lesson.users.count(), 1)
        self.assertEqual(lesson.users[0].user.id, user.id)
        self.assertEqual(lesson.users[0].mark, "4+")

        amid = lesson.auto_marks[0].id

        request = self.app.post('/lesson/%d/edit' % lesson.id, data={
            "name": 'Maximum',
            "contest_id": contest.id,
            "start": '2016-06-23 12:57',
            "end": '2016-06-23 12:58',
            ("am%d-required" % amid): 42,
            ("am%d-mark" % amid): "2+",
            ("am%d-points" % amid): -4
        }, follow_redirects=True)
        db.session.expire(lesson)
        self.assertEqual(request.status_code, 200)
        self.assertEqual(lesson.auto_marks.count(), 1)
        self.assertEqual(lesson.auto_marks[0].mark, "2+")
        self.assertEqual(lesson.auto_marks[0].required, 42)
        self.assertEqual(lesson.auto_marks[0].points, -4)
        self.assertEqual(request.status_code, 200)
        self.assertEqual(lesson.users.count(), 0)
        request = self.app.post('/lesson/%d/edit' % lesson.id, data={
            "name": 'Maximum',
            "contest_id": contest.id,
            "start": '2016-06-23 12:57',
            "end": '2016-06-23 12:58',
            ("am%d-delete" % amid): "on"
        }, follow_redirects=True)
        db.session.expire(lesson)
        self.assertEqual(request.status_code, 200)
        self.assertEqual(lesson.auto_marks.count(), 0)
        self.assertEqual(lesson.users.count(), 0)

        self.logout()
        lesson_id = lesson.id
        request = self.app.get('/lesson/%d/delete' % lesson_id, follow_redirects=True)
        self.assertEqual(request.status_code, 403)
        self.assertTrue(Lesson.query.get(lesson_id))
        self.login('admin', 'admin')
        request = self.app.get('/lesson/9001/delete', follow_redirects=True)
        self.assertEqual(request.status_code, 404)
        self.assertTrue(Lesson.query.get(lesson_id))
        request = self.app.get('/lesson/%d/delete' % lesson_id, follow_redirects=True)
        self.assertEqual(request.status_code, 200)
        self.assertFalse(Lesson.query.get(lesson_id))

    def test_notfound(self):
        request = self.app.get('/idontexist')
        self.assertEqual(request.status_code, 404)
        self.assertIn(b'PySistem', request.data)

    def test_problem_methods(self):
        problem1 = Problem(name='A+B', description='Add two numbers',
            statement='Just do it', time_limit=1234, memory_limit=54321)
        db.session.add(problem1)
        problem2 = Problem(name='1 to N', description='List all integers from 1 to N',
            statement='Please do it. Again.', time_limit=1234, memory_limit=54321)
        db.session.add(problem2)

        contest = Contest(name="<'Hello'>", start=datetime(2016, 1, 12),
            end=datetime(2016, 1, 25), freeze=datetime(2016, 1, 14),
            unfreeze_after_end=False, rules='acm')
        db.session.add(contest)
        db.session.commit()

        test_group = TestGroup(problem=problem1)
        test_group.score = 100
        db.session.add(test_group)
        db.session.commit()

        g.user = User()
        self.assertEqual(contest.get_freeze_time(), datetime(2016, 1, 14))
        contest.unfreeze_after_end = True
        self.assertEqual(contest.get_freeze_time(), datetime(2016, 1, 25))
        contest.unfreeze_after_end = False
        g.user = User.query.filter(User.username == 'admin').first()
        self.assertEqual(contest.get_freeze_time(), datetime(2016, 1, 25))
        self.assertEqual(contest.get_freeze_time(admin=False), datetime(2016, 1, 14))
        g.user = User()

        assoc1 = ContestProblemAssociation(prefix="A")
        assoc1.contest_id = contest.id
        assoc1.problem_id = problem1.id
        assoc2 = ContestProblemAssociation(prefix="B")
        assoc2.contest_id = contest.id
        assoc2.problem_id = problem2.id
        db.session.add(assoc1)
        db.session.add(assoc2)
        db.session.commit()

        admin = User.query.filter(User.username == 'admin').first()

        self.assertEqual(problem1.user_status(admin, color=False), '')
        self.assertEqual(problem1.user_status(admin, only_color=True), '')

        sub1 = Submission(user=admin, problem=problem1)
        sub1.status = STATUS_COMPILEFAIL
        sub1.result = RESULT_UNKNOWN
        sub1.submitted = datetime(2016, 1, 13)
        sub1.score = 0
        db.session.add(sub1)
        db.session.commit()
        self.assertEqual(problem1.user_status(admin, color=False), '')
        self.assertEqual(problem1.user_status(admin, only_color=True), '')

        sub2 = Submission(user=admin, problem=problem1)
        sub2.status = STATUS_DONE
        sub2.result = RESULT_WA
        sub2.submitted = datetime(2016, 1, 15)
        sub2.score = 42
        db.session.add(sub2)
        db.session.commit()
        self.assertEqual(problem1.user_status(admin, color=False), 'Wrong Answer')
        self.assertEqual(problem1.user_status(admin, only_color=True), 'danger')

        sub3 = Submission(user=admin, problem=problem1)
        sub3.status = STATUS_DONE
        sub3.result = RESULT_OK
        sub3.submitted = datetime(2016, 1, 17)
        sub3.score = 100
        db.session.add(sub3)
        db.session.commit()
        self.assertEqual(problem1.user_status(admin, color=False), 'Accepted')
        self.assertEqual(problem1.user_status(admin, only_color=True), 'success')

        sub4 = Submission(user=admin, problem=problem1)
        sub4.status = STATUS_DONE
        sub4.result = RESULT_WA
        sub4.submitted = datetime(2016, 1, 19)
        sub4.score = 79
        db.session.add(sub4)
        db.session.commit()
        self.assertEqual(problem1.user_status(admin, color=False), 'Accepted')
        self.assertEqual(problem1.user_status(admin, only_color=True), 'success')

        db.session.commit()
        self.assertEqual(problem1.get_user_failed_attempts(admin), 1)
        self.assertEqual(problem1.get_user_failed_attempts(admin, datetime(2016, 1, 14)), 0)
        self.assertEqual(problem1.get_user_failed_attempts(admin, datetime(2016, 1, 16)), 1)
        self.assertEqual(problem1.get_user_failed_attempts(admin, datetime(2016, 1, 18)), 1)
        self.assertEqual(problem1.get_user_failed_attempts(admin, datetime(2016, 1, 20)), 1)

        self.assertEqual(problem1.user_score(admin), (100, datetime(2016, 1, 19)))
        self.assertEqual(problem1.user_score(admin, datetime(2016, 1, 14)), (0, None))
        self.assertEqual(problem1.user_score(admin, datetime(2016, 1, 16)), (42, datetime(2016, 1, 15)))
        self.assertEqual(problem1.user_score(admin, datetime(2016, 1, 18)), (100, datetime(2016, 1, 17)))
        self.assertEqual(problem1.user_score(admin, datetime(2016, 1, 20)), (100, datetime(2016, 1, 19)))

        contest.rules = 'roi'
        self.assertEqual(contest.rate_user(admin), (0,))
        self.assertEqual(contest.rate_user(admin, do_freeze=False), (100,))
        contest.freeze = datetime(2016, 1, 16)
        self.assertEqual(contest.rate_user(admin), (42,))
        contest.freeze = datetime(2016, 1, 14)
        g.user = User.query.filter(User.username == 'admin').first()
        self.assertEqual(contest.rate_user(admin), (100,))
        g.user = User()

        contest.rules = 'acm'
        self.assertEqual(contest.rate_user(admin), (0, 0))
        self.assertEqual(contest.rate_user(admin, do_freeze=False), (1, 10100))
        contest.freeze = datetime(2016, 1, 16)
        self.assertEqual(contest.rate_user(admin), (0, 0))
        contest.freeze = datetime(2016, 1, 14)
        g.user = User.query.filter(User.username == 'admin').first()
        self.assertEqual(contest.rate_user(admin), (1, 10100))
        g.user = User()


    def change_password(self, new_password=None, new_password_confirm=None, old_password=None, username=None):
        return self.app.post('/user/%s/password' % username if username else '/user/password', data=dict(
            new_password=new_password,
            new_password_confirm=new_password_confirm,
            old_password=old_password
        ), follow_redirects=True)

    def test_change_password(self):
        request = self.change_password('ilovememes', 'ilovememes')
        self.assertEqual(request.status_code, 404)
        self.login('default', 'default')
        request = self.change_password('ilovememes', 'ilovememes')
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'Old password is incorrect', request.data)
        request = self.change_password('ilovemems', 'ilovememes', 'default')
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'New passwords do not match', request.data)
        request = self.change_password('i', 'i', 'default')
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'New password is too short', request.data)
        request = self.change_password('ilovememes', 'ilovememes', 'default')
        self.assertEqual(request.status_code, 200)
        default = User.query.filter(User.username == 'default').first()
        self.assertTrue(default)
        passwd = User.signpasswd('default', 'ilovememes')
        self.assertEqual(default.password, passwd)

        request = self.change_password('memesloveme', 'memesloveme', username='adminx')
        self.assertEqual(request.status_code, 404)
        request = self.change_password('memesloveme', 'memesloveme', username='admin')
        self.assertEqual(request.status_code, 403)
        admin = User.query.filter(User.username == 'admin').first()
        self.assertTrue(admin)
        passwd = User.signpasswd('admin', 'admin')
        self.assertEqual(admin.password, passwd)

        self.logout()
        self.login('admin', 'admin')

        request = self.change_password('memesloveme', 'memesloveme', username='defaultx')
        self.assertEqual(request.status_code, 404)
        request = self.change_password('memsloveme', 'memesloveme', username='default')
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'New passwords do not match', request.data)
        request = self.change_password('i', 'i', username='default')
        self.assertEqual(request.status_code, 200)
        self.assertIn(b'New password is too short', request.data)
        request = self.change_password('memesloveme', 'memesloveme', username='default')
        self.assertEqual(request.status_code, 200)
        db.session.expire(default)
        passwd = User.signpasswd('default', 'memesloveme')
        self.assertEqual(default.password, passwd)

    def test_automarks(self):
        lesson = Lesson(name='lessonname')
        db.session.add(lesson)
        db.session.commit()

        lesson.auto_marks.append(AutoMark("score", 50, "3", 4))
        lesson.auto_marks.append(AutoMark("score", 100, "5", 8))
        lesson.auto_marks.append(AutoMark("score", 75, "4", 5))

        lesson.auto_marks.append(AutoMark("place", 3, "4+", 6))
        lesson.auto_marks.append(AutoMark("place", 2, "5-", 7))
        lesson.auto_marks.append(AutoMark("place", 1, "5+", 9))

        db.session.commit()
        self.assertEqual(lesson.get_automarks(), (None, 0))
        self.assertEqual(lesson.get_automarks(score=49), (None, 0))
        self.assertEqual(lesson.get_automarks(score=50), ("3", 4))
        self.assertEqual(lesson.get_automarks(score=74), ("3", 4))
        self.assertEqual(lesson.get_automarks(score=75), ("4", 5))
        self.assertEqual(lesson.get_automarks(score=75, place=4), ("4", 5))
        self.assertEqual(lesson.get_automarks(score=75, place=3), ("4+", 6))
        self.assertEqual(lesson.get_automarks(score=25, place=3), ("4+", 6))
        self.assertEqual(lesson.get_automarks(place=3), ("4+", 6))
        self.assertEqual(lesson.get_automarks(score=100, place=3), ("5", 8))
        self.assertEqual(lesson.get_automarks(score=100, place=1), ("5+", 9))

