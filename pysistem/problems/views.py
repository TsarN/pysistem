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

@mod.route('/<int:problem_id>')
@yield_problem()
@guard_problem()
def view(problem_id, problem):
    """View problem's statement

    ROUTE arguments:
    problem_id -- Problem's ID

    Permissions required:
    Problem access
    """
    return render_template('problems/view.html', problem=problem)

@mod.route('/new')
def new():
    """Create new problem

    GET arguments:
    [contest_id] -- Contest's ID

    Permissions required:
    Contest Administrator (if contest_id)
    Server Administrator (if not contest_id)
    """
    contest_id = request.args.get('contest_id')
    if contest_id:
        contest = Contest.query.get(contest_id)
        if not contest:
            return render_template('errors/404.html'), 404
        if not g.user.is_admin(contest=contest):
            return render_template('errors/403.html'), 403
    else:
        if not g.user.is_admin():
            return render_template('errors/403.html'), 403
    return render_template('problems/edit.html', problem=Problem(), contest_id=contest_id)

@mod.route('/<int:problem_id>/edit', methods=['GET', 'POST'])
@mod.route('/new', methods=['POST'])
def edit(problem_id=-1):
    """Create/Update problem

    ROUTE arguments:
    problem_id -- Problem's ID

    Permissions required:
    Problem Administrator
    """
    error = None
    problem = Problem.query.get(problem_id)
    if request.method == 'POST':
        problem = problem or Problem()
        is_new = problem.id is None
        name = request.form.get('name', '')
        description = request.form.get('description', '')
        statement = request.form.get('statement', '')
        time_limit = request.form.get('time_limit', 1000)
        memory_limit = request.form.get('memory_limit', 65536)
        if is_new:
            contest_id = request.args.get('contest_id')
            if contest_id:
                contest = Contest.query.get(contest_id)
                if not contest:
                    return render_template('errors/404.html'), 404
                if not g.user.is_admin(contest=contest):
                    return render_template('errors/403.html'), 403
            else:
                if not g.user.is_admin():
                    return render_template('errors/403.html'), 403
        else:
            if not g.user.is_admin(problem=problem):
                return render_template('errors/403.html'), 403

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
                    return redirect(url_for('contests.problems', contest_id=redirect_to_contest))
                return redirect(url_for('problems.view', problem_id=problem.id))
            else:
                flash(gettext('problems.edit.success'))
                return redirect(url_for('problems.edit', problem_id=problem.id))
        else:
            error = gettext('problems.edit.emptyname')  
    else:
        if problem is None:
            return render_template('errors/404.html'), 404
        if not g.user.is_admin(problem=problem):
            return render_template('errors/403.html'), 403
    return render_template('problems/edit.html', problem=problem, error=error)

@mod.route('/<int:problem_id>/export')
@yield_problem()
@requires_admin(problem="problem")
def export(problem_id, problem):
    """Export problem to gzip-encoded file
    ROUTE arguments:
    problem_id -- Problem's ID

    Permissions required:
    Problem administrator
    """
    content = problem.export_gzip()
    response = Response(content, mimetype='application/gzip')
    response.headers['Content-Disposition'] = 'attachment; filename=%s.pysistem.gz' % problem.transliterate_name()
    return response

@mod.route('/import', methods=['POST'])
@requires_admin
def import_():
    """Create new problem from gzip-encoded file
    
    POST arguments:
    [contest_id] -- Contest's ID

    Permissions required:
    Contest Administrator (if contest_id)
    Server Administrator (if not contest_id)
    """
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
                return redirect(url_for('contests.problems', contest_id=redirect_to_contest))
            return redirect(url_for('problems.view', problem_id=problem.id))
    flash('::danger ' + gettext('problems.import.error'))
    return redirect(url_for('problems.new'))

@mod.route('/<int:problem_id>/delete')
@yield_problem()
@requires_admin(problem="problem")
def delete(problem_id, problem):
    """Delete problem from database    

    ROUTE arguments:
    problem_id -- Problem's ID

    Permissions required:
    Problem Administrator
    """
    for x in ContestProblemAssociation.query.filter( \
        ContestProblemAssociation.problem_id == problem.id):
        db.session.delete(x)
    db.session.delete(problem)
    db.session.commit()
    return redirect(url_for('index'))

@mod.route('/<int:problem_id>/tests')
@yield_problem()
@requires_admin(problem="problem")
def tests(problem_id, problem):
    """View and edit problem's test pairs    

    ROUTE arguments:
    problem_id -- Problem's ID

    Permissions required:
    Problem Administrator
    """
    test_groups = TestGroup.query.filter(TestGroup.problem_id == problem.id).all()
    return render_template('problems/tests.html', problem=problem, test_groups=test_groups)

@mod.route('/<int:problem_id>/testgroup/new', methods=['POST'])
@mod.route('/<int:problem_id>/testgroup/<int:group_id>', methods=['POST'])
@yield_problem()
@requires_admin(problem="problem")
def update_test_group(problem_id, problem, group_id=None):
    """Update/Create test pair group    

    ROUTE arguments:
    problem_id -- Problem's ID
    [group_id] -- TestGroup's ID

    Permissions required:
    Problem Administrator
    """
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

@mod.route('/deltestgroup/<int:test_group_id>', methods=['GET', 'POST'])
@yield_test_group()
@requires_admin(test_group="test_group")
def delete_test_group(test_group_id, test_group):
    """Delete test pair group   

    ROUTE arguments:
    test_group_id -- Problem's ID

    Permissions required:
    Problem Administrator
    """
    db.session.delete(test_group)
    db.session.commit()
    flash(gettext('problems.deltestgroup.success'))
    return redirect(redirect_url())

@mod.route('/deltest/<int:test_pair_id>', methods=['GET', 'POST'])
@yield_test_pair()
@requires_admin(test_pair="test")
def deltest(test_pair_id, test):
    """Delete test pair  

    ROUTE arguments:
    test_pair_id -- TestPair's ID

    Permissions required:
    Problem Administrator
    """
    db.session.delete(test)
    db.session.commit()
    flash(gettext('problems.deltest.success'))
    return redirect(redirect_url())

@mod.route('/addtest/<int:test_group_id>', methods=['POST'])
@yield_test_group()
@requires_admin(test_group="test_group")
def addtest(test_group_id, test_group):
    """Create new test in test group   

    ROUTE arguments:
    test_group_id -- TestGroup's ID

    Permissions required:
    Problem Administrator
    """
    input_str = ''
    pattern_str = ''

    if 'input_file' not in request.files:
        flash('::warning ' + gettext('problems.addtest.inputmissing'))
        return redirect(url_for('problems.tests', problem_id=test_group.problem_id))

    input_file = request.files['input_file']
    if input_file.filename == '':
        flash('::warning ' + gettext('problems.addtest.inputmissing'))
        return redirect(url_for('problems.tests', problem_id=test_group.problem_id))

    if input_file:
        input_str = input_file.stream.read().decode()

    if 'pattern_file' in request.files:
        pattern_file = request.files['pattern_file']
        if pattern_file and pattern_file.filename != '':
            pattern_str = pattern_file.stream.read().decode()

    test_pair = TestPair(input_str, pattern_str)
    test_group.test_pairs.append(test_pair)
    db.session.commit()
    return redirect(url_for('problems.tests', problem_id=test_group.problem_id))

@mod.route('/addtestzip/<int:test_group_id>', methods=['POST'])
@yield_test_group()
@requires_admin(test_group="test_group")
def addtestzip(test_group_id, test_group):
    """Create many tests in test group from ZIP file   

    ROUTE arguments:
    test_group_id -- TestGroup's ID

    Permissions required:
    Problem Administrator
    """
    if 'zip_file' not in request.files:
        flash('::warning ' + gettext('problems.addtestzip.inputmissing'))
        return redirect(url_for('problems.tests', problem_id=test_group.problem_id))

    zip_file = request.files['zip_file']
    if zip_file.filename == '':
        flash('::warning ' + gettext('problems.addtestzip.inputmissing'))
        return redirect(url_for('problems.tests', problem_id=test_group.problem_id))
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
        return redirect(url_for('problems.tests'), problem_id=test_group.problem_id)
    except: 
        flash('::danger ' + gettext('problems.addtestzip.invalid'))
        return redirect(url_for('problems.tests', problem_id=test_group.problem_id))

@mod.route('/<int:problem_id>/checkers')
@yield_problem()
@requires_admin(problem="problem")
def checkers(problem_id, problem):
    """View and edit problem's checkers   

    ROUTE arguments:
    problem_id -- Problem's ID

    Permissions required:
    Problem Administrator
    """
    checkers = Checker.query.filter(Checker.problem_id == problem.id).all()
    compilers = Compiler.query.all()
    return render_template('problems/checkers.html', problem=problem,
        checkers=checkers, compilers=compilers)

@mod.route('/<int:problem_id>/addchecker', methods=['POST'])
@yield_problem()
@requires_admin(problem="problem")
def addchecker(problem_id, problem):
    """Add new checker

    ROUTE arguments:
    problem_id -- Problem's ID

    Permissions required:
    Problem Administrator
    """
    source = ''

    if 'source_file' not in request.files:
        flash('::warning ' + gettext('problems.addchecker.sourcemissing'))
        return redirect(url_for('problems.checkers', problem_id=problem_id))

    source_file = request.files['source_file']
    if source_file.filename == '':
        flash('::warning ' + gettext('problems.addchecker.sourcemissing'))
        return redirect(url_for('problems.checkers', problem_id=problem_id))

    if source_file:
        source = source_file.stream.read().decode()

    name = request.form.get('name', '')
    compiler_id = request.form.get('compiler', -1)
    compiler = Compiler.query.get(compiler_id)
    if not compiler:
        return render_template('errors/404.html'), 404

    checker = Checker(name, source, problem)
    checker.compiler_id = compiler.id
    db.session.add(checker)
    db.session.commit()
    checker.compile()
    return redirect(url_for('problems.checkers', problem_id=problem_id))

@mod.route('/delchecker/<int:checker_id>', methods=['GET', 'POST'])
@yield_checker()
@requires_admin(checker="checker")
def delchecker(checker_id, checker):
    """Delete checker

    ROUTE arguments:
    checker_id -- Checker's ID

    Permissions required:
    Problem Administrator
    """
    db.session.delete(checker)
    db.session.commit()
    flash(gettext('problems.delchecker.success'))
    return redirect(redirect_url())

@mod.route('/actchecker/<int:checker_id>', methods=['GET', 'POST'])
@yield_checker()
@requires_admin(checker="checker")
def actchecker(checker_id, checker):
    """Make chekcer active    

    ROUTE arguments:
    checker_id -- Checker's ID

    Permissions required:
    Problem Administrator
    """
    checker.set_act()
    flash(gettext('problems.actchecker.success'))
    return redirect(redirect_url())

@mod.route('/checkercompilelog/<int:checker_id>')
@yield_checker()
@requires_admin(checker="checker")
def checkercompilelog(checker_id, checker):
    """Return checker's compilation log

    ROUTE arguments:
    checker_id -- Checker's ID

    Permissions required:
    Problem Administrator
    """
    return Response(checker.compile_log, mimetype='text/plain')

@mod.route('/<int:problem_id>/submissions', methods=['GET', 'POST'])
@mod.route('/<int:problem_id>/submissions/user/<username>')
@requires_login
@yield_problem()
@guard_problem()
def submissions(problem_id, problem, username=None):
    """View user's submissions or submit new 

    ROUTE arguments:
    problem_id -- Problem's ID
    [username] -- User's username

    Permissions required:
    Logged In
    Problem Access
    Problem Administrator (for viewing other user's submissions)
    """
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
            return redirect(url_for('problems.submissions', problem_id=problem_id))

        source_file = request.files['source_file']
        if source_file.filename == '':
            flash('::warning ' + gettext('problems.submit.sourcemissing'))
            return redirect(url_for('problems.submissions', problem_id=problem_id))

        if source_file:
            source = source_file.stream.read().decode()

        compiler_id = request.form.get('compiler', None)
        compiler = Compiler.query.get(int(compiler_id))
        if compiler is None:
            flash('::warning ' + gettext('problems.submit.selectcompiler'))
            return redirect(url_for('problems.submissions', problem_id=problem_id))

        sub = Submission(source, g.user.id, compiler.id, problem.id)
        sub.status = STATUS_CWAIT
        sub.current_test_id = 0
        db.session.add(sub)
        db.session.commit()
        flash(gettext('problems.submit.success'))
        return redirect(url_for('problems.submissions', problem_id=problem_id))

    submissions = Submission.query.filter(db.and_(
        Submission.problem_id == problem.id, Submission.user_id == user.id)).all()
    compilers = Compiler.query.all()

    rendered_subs = render_template('submissions/list.html', submissions=submissions)

    attempted_users = None
    if g.user.is_admin(problem=problem_id):
        attempted_users = User.query.filter(User.submissions.any(
            Submission.problem_id == problem.id)).all()

    return render_template('problems/submissions.html', \
        problem=problem, compilers=compilers, rendered_subs=rendered_subs,
        attempted_users=attempted_users, user=user)
