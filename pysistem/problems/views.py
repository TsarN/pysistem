# -*- coding: utf-8 -*-
from pysistem import app, babel, db, redirect_url
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from pysistem.problems.model import Problem
from pysistem.problems.decorators import yield_problem, guard_problem
from pysistem.test_pairs.decorators import yield_test_pair, yield_test_group
from pysistem.checkers.decorators import yield_checker
from pysistem.test_pairs.model import TestPair, TestGroup
from pysistem.checkers.model import Checker
from pysistem.submissions.model import Submission
from pysistem.compilers.model import Compiler
from pysistem.users.model import User
from pysistem.contests.model import Contest, ContestProblemAssociation
from pysistem.users.decorators import requires_login, requires_admin
from flask_babel import gettext
from werkzeug.utils import secure_filename
from zipfile import ZipFile
from pysistem.submissions.const import *

mod = Blueprint('problems', __name__, url_prefix='/problem')

@mod.route('/<int:id>')
@yield_problem()
@guard_problem()
def view(id, problem):
    """View problem's statement"""
    return render_template('problems/view.html', problem=problem)

@mod.route('/new')
@requires_admin
def new():
    """Create new problem"""
    contest_id = request.args.get('contest_id')
    return render_template('problems/edit.html', problem=Problem(), contest_id=contest_id)

@mod.route('/<int:id>/edit', methods=['GET', 'POST'])
@mod.route('/new/post', methods=['POST'])
@requires_admin
def edit(id=-1):
    """Create/Update problem"""
    error = None
    problem = Problem.query.get(id)
    if request.method == 'POST':
        problem = problem or Problem()
        is_new = problem.id is None
        name = request.form.get('name', '')
        description = request.form.get('description', '')
        statement = request.form.get('statement', '')
        time_limit = request.form.get('time_limit', 1000)
        memory_limit = request.form.get('memory_limit', 65536)

        if len(name.strip(' \t\n\r')) > 0:
            problem.name = name
            problem.description = description
            problem.statement = statement
            problem.time_limit = int(time_limit)
            problem.memory_limit = int(memory_limit)
            redirect_to_contest = None
            if is_new:
                db.session.add(problem)
                if request.args.get('contest_id'):
                    contest = Contest.query.get(int(request.args.get('contest_id')))
                    if contest is not None:
                        assoc = ContestProblemAssociation()
                        assoc.contest = contest
                        assoc.problem = problem
                        contest.problems.append(assoc)
                        redirect_to_contest = contest.id
            db.session.commit()
            if is_new:
                flash(gettext('problems.new.success'))
                if redirect_to_contest:
                    return redirect(url_for('contests.problems', id=redirect_to_contest))
                return redirect(url_for('problems.view', id=problem.id))
            else:
                flash(gettext('problems.edit.success'))
                return redirect(url_for('problems.edit', id=problem.id))
        else:
            error = gettext('problems.edit.emptyname')  
    else:
        if problem is None:
            return render_template('errors/404.html'), 404
    return render_template('problems/edit.html', problem=problem, error=error)

@mod.route('/<int:id>/export')
@yield_problem()
@requires_admin(problem="problem")
def export(id, problem):
    """Export problem to gzip-encoded file"""
    content = problem.export_gzip()
    response = Response(content, mimetype='application/gzip')
    response.headers['Content-Disposition'] = 'attachment; filename=%s.pysistem.gz' % problem.transliterate_name()
    return response

@mod.route('/import', methods=['POST'])
@requires_admin
def import_():
    """Create new problem from gzip-encoded file"""
    problem = Problem()
    if 'import_file' not in request.files:
        flash('::warning ' + gettext('problems.import.filemissing'))
        return redirect(url_for('problems.new'))

    import_file = request.files['import_file']
    if import_file.filename == '':
        flash('::warning ' + gettext('problems.import.filemissing'))
        return redirect(url_for('problems.new'))

    if import_file:
        if problem.import_gzip(import_file.stream.read()):
            db.session.add(problem)
            redirect_to_contest = None
            if request.args.get('contest_id'):
                contest = Contest.query.get(int(request.args.get('contest_id')))
                if contest is not None:
                    assoc = ContestProblemAssociation()
                    assoc.contest = contest
                    assoc.problem = problem
                    contest.problems.append(assoc)
                    redirect_to_contest = contest.id
            db.session.commit()
            if redirect_to_contest:
                return redirect(url_for('contests.problems', id=redirect_to_contest))
            return redirect(url_for('problems.view', id=problem.id))
    flash('::danger ' + gettext('problems.import.error'))
    return redirect(url_for('problems.new'))

@mod.route('/<int:id>/delete')
@yield_problem()
@requires_admin(problem="problem")
def delete(id, problem):
    """Delete problem from database"""
    for x in ContestProblemAssociation.query.filter( \
        ContestProblemAssociation.problem_id == problem.id):
        db.session.delete(x)
    db.session.delete(problem)
    db.session.commit()
    return redirect(url_for('index'))

@mod.route('/<int:id>/tests')
@yield_problem()
@requires_admin(problem="problem")
def tests(id, problem):
    """View and edit problem's test pairs"""
    test_groups = TestGroup.query.filter(TestGroup.problem_id == problem.id).all()
    return render_template('problems/tests.html', problem=problem, test_groups=test_groups)

@mod.route('/<int:id>/testgroup/new', methods=['POST'])
@mod.route('/<int:id>/testgroup/<int:group_id>', methods=['POST'])
@yield_problem()
@requires_admin(problem="problem")
def update_test_group(id, problem, group_id=None):
    """Update/Create test pair group"""
    test_group = (TestGroup.query.get(group_id) if group_id else None) or TestGroup()
    is_new = test_group.id is None
    test_group.score = int(request.form.get('score', test_group.score))
    test_group.score_per_test = int(request.form.get('score_per_test', test_group.score_per_test))
    test_group.check_all = bool(request.form.get('check_all'))
    if is_new:
        problem.test_groups.append(test_group)
        flash(gettext('problems.addtestgroup.success'))
    else:
        flash(gettext('problems.modtestgroup.success'))
    db.session.add(test_group)
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/deltestgroup/<int:id>', methods=['GET', 'POST'])
@yield_test_group()
@requires_admin(test_group="test_group")
def delete_test_group(id, test_group):
    """Delete test pair group"""
    db.session.delete(test_group)
    db.session.commit()
    flash(gettext('problems.deltestgroup.success'))
    return redirect(redirect_url())

@mod.route('/deltest/<int:id>', methods=['GET', 'POST'])
@yield_test_pair()
@requires_admin(test_pair="test")
def deltest(id, test):
    """Delete test pair"""
    db.session.delete(test)
    db.session.commit()
    flash(gettext('problems.deltest.success'))
    return redirect(redirect_url())

@mod.route('/addtest/<int:id>', methods=['POST'])
@yield_test_group()
@requires_admin(test_group="test_group")
def addtest(id, test_group):
    """Create new test in test group"""
    input_str = ''
    pattern_str = ''

    if 'input_file' not in request.files:
        flash('::warning ' + gettext('problems.addtest.inputmissing'))
        return redirect(url_for('problems.tests', id=test_group.problem_id))

    input_file = request.files['input_file']
    if input_file.filename == '':
        flash('::warning ' + gettext('problems.addtest.inputmissing'))
        return redirect(url_for('problems.tests', id=test_group.problem_id))

    if input_file:
        input_str = input_file.stream.read().decode()

    if 'pattern_file' in request.files:
        pattern_file = request.files['pattern_file']
        if pattern_file and pattern_file.filename != '':
            pattern_str = pattern_file.stream.read().decode()

    test_pair = TestPair(input_str, pattern_str)
    test_group.test_pairs.append(test_pair)
    db.session.commit()
    return redirect(url_for('problems.tests', id=test_group.problem_id))

@mod.route('/addtestzip/<int:id>', methods=['POST'])
@yield_test_group()
@requires_admin(test_group="test_group")
def addtestzip(id, test_group):
    """Create many tests in test group from ZIP file"""
    if 'zip_file' not in request.files:
        flash('::warning ' + gettext('problems.addtestzip.inputmissing'))
        return redirect(url_for('problems.tests', id=test_group.problem_id))

    zip_file = request.files['zip_file']
    if zip_file.filename == '':
        flash('::warning ' + gettext('problems.addtestzip.inputmissing'))
        return redirect(url_for('problems.tests', id=test_group.problem_id))
    try:
        assert(zip_file)
        zf = ZipFile(zip_file.stream, mode="r")
        input_names = sorted(list(filter(lambda x: x.find('input') != -1, zf.namelist())))
        pattern_names = sorted(list(filter(lambda x: x.find('pattern') != -1, zf.namelist())))

        for i in range(len(input_names)):
            inp = zf.read(input_names[i]).decode()
            if len(pattern_names) <= i:
                pat = ""
            else:
                pat = zf.read(pattern_names[i]).decode()

            test_group.test_pairs.append(TestPair(inp, pat))
        db.session.commit()
        flash(gettext('problems.addtestzip.success'))
        return redirect(url_for('problems.tests'), id=test_group.problem_id)
    except: 
        flash('::danger ' + gettext('problems.addtestzip.invalid'))
        return redirect(url_for('problems.tests', id=test_group.problem_id))

@mod.route('/<int:id>/checkers')
@yield_problem()
@requires_admin(problem="problem")
def checkers(id, problem):
    """View and edit problem's checkers"""
    checkers = Checker.query.filter(Checker.problem_id == problem.id).all()
    return render_template('problems/checkers.html', problem=problem, checkers=checkers)

@mod.route('/<int:id>/addchecker', methods=['POST'])
@yield_problem()
@requires_admin(problem="problem")
def addchecker(id, problem):
    """Add new checker"""
    source = ''

    if 'source_file' not in request.files:
        flash('::warning ' + gettext('problems.addchecker.sourcemissing'))
        return redirect(url_for('problems.checkers', id=id))

    source_file = request.files['source_file']
    if source_file.filename == '':
        flash('::warning ' + gettext('problems.addchecker.sourcemissing'))
        return redirect(url_for('problems.checkers', id=id))

    if source_file:
        source = source_file.stream.read().decode()

    name = request.form.get('name', '')
    lang = request.form.get('lang', 'c')

    checker = Checker(name, source, problem, lang)
    db.session.add(checker)
    db.session.commit()
    checker.compile()
    return redirect(url_for('problems.checkers', id=id))

@mod.route('/delchecker/<int:id>', methods=['GET', 'POST'])
@yield_checker()
@requires_admin(problem="problem")
def delchecker(id, checker):
    """Delete checker"""
    db.session.delete(checker)
    db.session.commit()
    flash(gettext('problems.delchecker.success'))
    return redirect(redirect_url())

@mod.route('/actchecker/<int:id>', methods=['GET', 'POST'])
@yield_checker()
@requires_admin(problem="problem")
def actchecker(id, checker):
    """Make chekcer active"""
    checker.set_act()
    flash(gettext('problems.actchecker.success'))
    return redirect(redirect_url())

@mod.route('/<int:id>/submissions', methods=['GET', 'POST'])
@mod.route('/<int:id>/submissions/user/<username>')
@requires_login
@yield_problem()
@guard_problem()
def submissions(id, problem, username=None):
    """View user's submissions or submit new"""
    user = g.user
    if username is not None:
        user = User.query.filter( \
                db.func.lower(User.username) == db.func.lower(username)).first()
        if user is None:
            return render_template('errors/404.html'), 404
        if not g.user.is_admin(problem=problem) and (user.id != g.user.id):
            return render_template('errors/403.html'), 403

    if request.method == 'POST':
        source = ''

        if 'source_file' not in request.files:
            flash('::warning ' + gettext('problems.submit.sourcemissing'))
            return redirect(url_for('problems.submissions', id=id))

        source_file = request.files['source_file']
        if source_file.filename == '':
            flash('::warning ' + gettext('problems.submit.sourcemissing'))
            return redirect(url_for('problems.submissions', id=id))

        if source_file:
            source = source_file.stream.read().decode()

        compiler_id = request.form.get('compiler', None)
        compiler = Compiler.query.get(int(compiler_id))
        if compiler is None:
            flash('::warning ' + gettext('problems.submit.selectcompiler'))
            return redirect(url_for('problems.submissions', id=id))

        sub = Submission(source, g.user.id, compiler.id, problem.id)
        sub.status = STATUS_CWAIT
        sub.current_test_id = 0
        db.session.add(sub)
        db.session.commit()
        flash(gettext('problems.submit.success'))
        return redirect(url_for('problems.submissions', id=id))

    submissions = Submission.query.filter(db.and_(
        Submission.problem_id == problem.id, Submission.user_id == user.id)).all()
    compilers = Compiler.query.all()

    rendered_subs = render_template('submissions/list.html', submissions=submissions)

    attempted_users = None
    if g.user.role == 'admin':
        attempted_users = User.query.filter(User.submissions.any(
            Submission.problem_id == problem.id)).all()

    return render_template('problems/submissions.html', \
        problem=problem, compilers=compilers, rendered_subs=rendered_subs,
        attempted_users=attempted_users, user=user)