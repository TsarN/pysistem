# -*- coding: utf-8 -*-
from pysistem import app, babel, db, redirect_url
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint
from flask_babel import gettext
from pysistem.contests.model import Contest
from pysistem.users.model import User
from pysistem.problems.model import Problem
from pysistem.users.decorators import requires_login, requires_admin
from datetime import datetime

mod = Blueprint('contests', __name__, url_prefix='/contest')

@mod.route('/<int:id>/linkwith/<int:problem_id>')
@requires_admin
def linkwith(id, problem_id):
    contest = Contest.query.get(id)
    if contest is None:
        return render_template('errors/404.html'), 404
    problem = Problem.query.get(problem_id)
    if problem is None:
        return render_template('errors/404.html'), 404
    contest.problems.append(problem)
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/<int:id>/unlinkwith/<int:problem_id>')
@requires_admin
def unlinkwith(id, problem_id):
    contest = Contest.query.get(id)
    if contest is None:
        return render_template('errors/404.html'), 404
    problem = Problem.query.get(problem_id)
    if problem is None:
        return render_template('errors/404.html'), 404
    contest.problems.remove(problem)
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/<int:id>')
def problems(id):
    contest = Contest.query.get(id)
    if contest is None:
        return render_template('errors/404.html'), 404
    addable_problems = Problem.query.all()
    if (g.user.role == 'admin') and (len(contest.problems) > 0):
        addable_problems = \
        Problem.query.filter(~Problem.id.in_([x.id for x in contest.problems])).all()
    return render_template('contests/problems.html', contest=contest, addable_problems=addable_problems)

@mod.route('/new')
def new():
    return render_template('contests/edit.html', contest=Contest())

@mod.route('/<int:id>/edit', methods=['GET', 'POST'])
@mod.route('/new/post', methods=['POST'])
@requires_admin
def edit(id=-1):
    contest = Contest.query.get(id)
    error = None
    if request.method == 'POST':
        contest = contest or Contest()
        is_new = contest.id is None
        name = request.form.get('name', '')
        start = datetime.strptime(request.form.get('start', g.now_formatted), "%Y-%m-%d %H:%M")
        end = datetime.strptime(request.form.get('end', g.now_formatted), "%Y-%m-%d %H:%M")
        freeze = datetime.strptime(request.form.get('freeze', g.now_formatted), "%Y-%m-%d %H:%M")

        if (start > freeze) or (freeze > end) or (start > end) or not \
            (start and end and freeze):
            error = gettext('contests.edit.invaliddates')
        else:
            if len(name.strip(' \t\n\r')) > 0:
                contest.name = name
                contest.start = start
                contest.end = end
                contest.freeze = freeze
                if is_new:
                    db.session.add(contest)
                db.session.commit()
                if is_new:
                    flash(gettext('contests.new.success'))
                    return redirect(url_for('contests.problems', id=contest.id))
                else:
                    flash(gettext('contests.edit.success'))
                    return redirect(url_for('contests.edit', id=contest.id))
            else:
                error = gettext('contests.edit.emptyname')

    if contest is None:
        return render_template('errors/404.html'), 404
    return render_template('contests/edit.html', contest=contest, error=error)

@mod.route('<int:id>/delete')
@requires_admin
def delete(id):
    contest = Contest.query.get(id)
    if contest is None:
        return render_template('errors/404.html'), 404
    db.session.delete(contest)
    db.session.commit()
    return redirect(url_for('index'))

def format_time(mins):
    if mins is None:
        return ''
    hour = mins // 60
    mins = mins % 60
    return ("0" * (hour < 10) + str(hour)) + ':' + \
           ("0" * (mins < 10) + str(mins))

@mod.route('/<int:id>/scoreboard')
def scoreboard(id):
    contest = Contest.query.get(id)
    if contest is None:
        return render_template('errors/404.html'), 404
    problems = contest.problems
    users = []
    for user in User.query.all():
        score = contest.rate_user(user)
        solved_map = {}
        for problem in problems:
            succeed, submitted = problem.user_succeed(user, freeze=contest.get_freeze_time())
            time = None
            if submitted is not None:
                time = int(max(0, (submitted - contest.start).total_seconds() // 60))
            solved_map[problem.id] = {
                "succeed": succeed,
                "time": format_time(time),
                "failed": problem.get_user_failed_attempts(user, freeze=contest.get_freeze_time())
            }
        users.append({
            "id": user.id,
            "score": score,
            "username": user.username,
            "is_solved": solved_map
        })
    users.sort(key=lambda x:(-x['score'][0], x['score'][1]))

    return render_template('contests/scoreboard.html',
        contest=contest, problems=problems, users=users)