from pysistem import app, babel, db, redirect_url
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from pysistem.problems.model import Problem
from pysistem.test_pairs.model import TestPair
from pysistem.checkers.model import Checker
from pysistem.submissions.model import Submission
from pysistem.submissions.const import *
from pysistem.compilers.model import Compiler
from pysistem.users.model import User
from pysistem.users.decorators import requires_login, requires_admin
from flask_babel import gettext
from werkzeug.utils import secure_filename

mod = Blueprint('problems', __name__, url_prefix='/problem')

@mod.route('/<int:id>')
def view(id):
    error = None
    problem = Problem.query.get(id)
    if problem is None:
        return render_template('errors/404.html'), 404
    return render_template('problems/view.html', problem=problem, error=error)

@mod.route('/new')
@requires_admin
def new():
    return render_template('problems/edit.html', problem=Problem())

@mod.route('/<int:id>/edit', methods=['GET', 'POST'])
@mod.route('/new/post', methods=['POST'])
@requires_admin
def edit(id=-1):
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
            if is_new:
                db.session.add(problem)
            db.session.commit()
            if is_new:
                flash(gettext('problems.new.success'))
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
@requires_admin
def export(id):
    problem = Problem.query.get(id)
    if problem is None:
        return render_template('errors/404.html'), 404
    content = problem.export_gzip()
    response = Response(content, mimetype='application/gzip')
    response.headers['Content-Disposition'] = 'attachment; filename=%s.pysistem.gz' % problem.transliterate_name()
    return response

@mod.route('/import', methods=['POST'])
@requires_admin
def import_():
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
            db.session.commit()
            return redirect(url_for('problems.view', id=problem.id))
    flash('::danger ' + gettext('problems.import.error'))
    return redirect(url_for('problems.new'))

@mod.route('/<int:id>/delete')
@requires_admin
def delete(id):
    problem = Problem.query.get(id)
    if problem is None:
        return render_template('errors/404.html'), 404
    db.session.delete(problem)
    db.session.commit()
    return redirect(url_for('index'))

@mod.route('/<int:id>/tests', methods=['GET', 'POST'])
@requires_admin
def tests(id):
    error = None
    problem = Problem.query.get(id)
    if problem is None:
        return render_template('errors/404.html'), 404

    tests = TestPair.query.filter(TestPair.problem_id == problem.id).all()
    return render_template('problems/tests.html', problem=problem, tests=tests, error=error)

@mod.route('/deltest/<int:id>', methods=['GET', 'POST'])
@requires_admin
def deltest(id):
    test = TestPair.query.get(id)
    if test is None:
        flash('::danger ' + gettext('problems.test.notfound'))
    else:
        db.session.delete(test)
        db.session.commit()
        flash(gettext('problems.deltest.success'))

    return redirect(redirect_url())

@mod.route('/addtest/<int:id>', methods=['POST'])
@requires_admin
def addtest(id):
    problem = Problem.query.get(id)
    if problem is None:
        return render_template('errors/404.html'), 404

    input_str = ''
    pattern_str = ''

    if 'input_file' not in request.files:
        flash('::warning ' + gettext('problems.addtest.inputmissing'))
        return redirect(url_for('problems.tests', id=id))

    input_file = request.files['input_file']
    if input_file.filename == '':
        flash('::warning ' + gettext('problems.addtest.inputmissing'))
        return redirect(url_for('problems.tests', id=id))

    if input_file:
        input_str = input_file.stream.read().decode()

    if 'pattern_file' in request.files:
        pattern_file = request.files['pattern_file']
        if pattern_file and pattern_file.filename != '':
            pattern_str = pattern_file.stream.read().decode()

    db.session.add(TestPair(input_str, pattern_str, problem))
    db.session.commit()
    return redirect(url_for('problems.tests', id=id))

@mod.route('/<int:id>/checkers')
@requires_admin
def checkers(id):
    problem = Problem.query.get(id)
    if problem is None:
        return render_template('errors/404.html'), 404

    checkers = Checker.query.filter(Checker.problem_id == problem.id).all()
    return render_template('problems/checkers.html', problem=problem, checkers=checkers)

@mod.route('/<int:id>/addchecker', methods=['POST'])
@requires_admin
def addchecker(id):
    problem = Problem.query.get(id)
    if problem is None:
        return render_template('errors/404.html'), 404

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
@requires_admin
def delchecker(id):
    checker = Checker.query.get(id)
    if checker is None:
        flash('::danger ' + gettext('problems.checker.notfound'))
    else:
        db.session.delete(checker)
        db.session.commit()
        flash(gettext('problems.delchecker.success'))

    return redirect(redirect_url())

@mod.route('/actchecker/<int:id>', methods=['GET', 'POST'])
@requires_admin
def actchecker(id):
    checker = Checker.query.get(id)
    if checker is None:
        flash('::danger ' + gettext('problems.checker.notfound'))
    else:
        checker.set_act()
        flash(gettext('problems.actchecker.success'))
        
    return redirect(redirect_url())

@mod.route('/<int:id>/submissions', methods=['GET', 'POST'])
@requires_login
def submissions(id, username=None):
    problem = Problem.query.get(id)
    if problem is None:
        return render_template('errors/404.html'), 404

    user = g.user
    if username is not None:
        user = User.query.filter( \
                db.func.lower(User.username) == db.func.lower(username)).first()
        if user is None:
            return render_template('errors/404.html'), 404

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
        db.session.commit()
        sub.async_check()
        flash(gettext('problems.submit.success'))
        return redirect(url_for('problems.submissions', id=id))

    submissions = Submission.query.filter(db.and_(
        Submission.problem_id == problem.id, Submission.user_id == user.id)).all()
    compilers = Compiler.query.all()

    return render_template('problems/submissions.html', \
        problem=problem, submissions=submissions, compilers=compilers)

@mod.route('/<int:id>/submissions/user/<username>', methods=['GET', 'POST'])
@requires_admin
def submissions_user(id, username):
    return submissions(id, username)

@mod.route('/submission/<int:id>/recheck')
@requires_admin
def rechecksub(id):
    submission = Submission.query.get(id)
    if submission is None:
        return render_template('errors/404.html'), 404
    submission.status = STATUS_CWAIT
    db.session.commit()
    submission.async_check()
    return redirect(redirect_url())

@mod.route('/submission/<int:id>/reject')
@requires_admin
def rejectsub(id):
    submission = Submission.query.get(id)
    if submission is None:
        return render_template('errors/404.html'), 404
    submission.result = RESULT_RJ
    submission.status = STATUS_DONE
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/submission/<int:id>/delete')
@requires_admin
def delsub(id):
    submission = Submission.query.get(id)
    if submission is None:
        return render_template('errors/404.html'), 404
    db.session.delete(submission)
    db.session.commit()
    return redirect(redirect_url())