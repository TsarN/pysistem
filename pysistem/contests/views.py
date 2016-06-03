from pysistem import app, babel, db
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint
from flask_babel import gettext
from pysistem.contests.model import Contest
from pysistem.users.model import User
from pysistem.problems.model import Problem

mod = Blueprint('contests', __name__, url_prefix='/contest')

@mod.route('/<int:id>')
def main(id):
    contest = Contest.query.get(id)
    if contest is None:
        return render_template('errors/404.html'), 404
    return render_template('contests/main.html', contest=contest)

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
            succeed, submitted = problem.user_succeed(user)
            time = None
            if submitted is not None:
                time = int(max(0, (submitted - contest.start).total_seconds() // 60))
            solved_map[problem.id] = {
                "succeed": succeed,
                "time": format_time(time),
                "failed": problem.get_user_failed_attempts(user)
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