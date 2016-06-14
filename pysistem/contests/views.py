# -*- coding: utf-8 -*-
from pysistem import app, babel, db, redirect_url, cache
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint
from flask_babel import gettext
from pysistem.contests.model import Contest, ContestProblemAssociation, contest_rulesets
from pysistem.users.model import User
from pysistem.problems.model import Problem
from pysistem.users.decorators import requires_login, requires_admin
from pysistem.contests.decorators import yield_contest
from pysistem.problems.decorators import yield_problem
from datetime import datetime
from pysistem.groups.model import Group, GroupContestAssociation, GroupUserAssociation

mod = Blueprint('contests', __name__, url_prefix='/contest')

@mod.route('/<int:id>/linkwith/<int:problem_id>')
@yield_contest()
@requires_admin(contest="contest")
@yield_problem(field='problem_id')
def linkwith(id, problem_id, contest, problem):
    """Add problem to contest"""
    assoc = ContestProblemAssociation()
    assoc.contest = contest
    assoc.problem = problem
    contest.problems.append(assoc)
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/<int:id>/unlinkwith/<int:problem_id>')
@yield_contest()
@requires_admin(contest="contest")
@yield_problem(field='problem_id')
def unlinkwith(id, problem_id, contest, problem):
    """Remove problem from contest"""
    assoc = ContestProblemAssociation.query.filter(db.and_(
        ContestProblemAssociation.contest_id == id,
        ContestProblemAssociation.problem_id == problem_id)).first()
    db.session.delete(assoc)
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/<int:id>/problemprefix/<int:problem_id>', methods=['GET', 'POST'])
@yield_contest()
@requires_admin(contest="id")
@yield_problem(field="problem_id")
def problemprefix(id, problem_id, contest, problem):
    """Update problem prefix in contest"""
    assoc = ContestProblemAssociation.query.filter(db.and_(
        ContestProblemAssociation.contest_id == id,
        ContestProblemAssociation.problem_id == problem_id)).first()
    assoc.prefix = request.values.get('prefix', assoc.prefix)
    db.session.commit();
    if request.method == 'POST':
        return 'success'
    else:
        return redirect(redirect_url())

@mod.route('/<int:id>')
@yield_contest()
def problems(id, contest):
    """Show contest's problems"""
    addable_problems = Problem.query.all()
    if g.user.is_admin(contest=contest) and (len(contest.problems) > 0):
        addable_problems = \
        Problem.query.filter(~Problem.id.in_([x.id for x in contest.problems])).all()
    return render_template('contests/problems.html', contest=contest, addable_problems=addable_problems)

@mod.route('/new')
def new():
    """Create new contest"""
    return render_template('contests/edit.html', contest=Contest(), contest_rulesets=contest_rulesets)

@mod.route('/<int:id>/edit', methods=['GET', 'POST'])
@mod.route('/new/post', methods=['POST'])
@requires_admin(contest="id")
def edit(id=-1):
    """Create/Update contest"""
    contest = Contest.query.get(id)
    error = None

    if g.user.is_admin():
        admin_groups = Group.query.all()
    else:
        admin_groups = Group.query.filter(Group.users.any(db.and_( \
            GroupUserAssociation.user_id == g.user.id, \
            GroupUserAssociation.role == 'admin')))

    if request.method == 'POST':
        contest = contest or Contest()
        is_new = contest.id is None
        name = request.form.get('name', '')
        start = datetime.strptime(request.form.get('start', g.now_formatted), "%Y-%m-%d %H:%M")
        end = datetime.strptime(request.form.get('end', g.now_formatted), "%Y-%m-%d %H:%M")
        freeze = datetime.strptime(request.form.get('freeze', g.now_formatted), "%Y-%m-%d %H:%M")
        unfreeze_after_end = bool(request.form.get('unfreeze_after_end', False))
        rules = request.form.get('ruleset', 'acm')

        group_test = any([g.user.is_admin()] + \
            [bool(request.form.get('group-%d' % group.id, False)) \
            for group in admin_groups])

        if (start > freeze) or (freeze > end) or (start > end) or not \
            (start and end and freeze):
            error = gettext('contests.edit.invaliddates')
        else:
            if len(name.strip(' \t\n\r')) > 0:
                if group_test:
                    contest.name = name
                    contest.start = start
                    contest.end = end
                    contest.freeze = freeze
                    contest.unfreeze_after_end = unfreeze_after_end
                    contest.rules = rules if rules in contest_rulesets.keys() else 'acm'

                    if is_new:
                        db.session.add(contest)

                    for group in admin_groups:
                        ch = bool(request.form.get('group-%d' % group.id, False))
                        assoc = None
                        if not is_new:
                            assoc = GroupContestAssociation.query.filter(db.and_( \
                                GroupContestAssociation.contest_id == contest.id, \
                                GroupContestAssociation.group_id == group.id      \
                                )).first()
                        if assoc and not ch:
                            db.session.delete(assoc)
                        if not assoc and ch:
                            assoc = GroupContestAssociation()
                            assoc.contest_id = contest.id
                            assoc.group_id = group.id
                            db.session.add(assoc)

                    db.session.commit()
                    if is_new:
                        flash(gettext('contests.new.success'))
                        return redirect(url_for('contests.problems', id=contest.id))
                    else:
                        flash(gettext('contests.edit.success'))
                        return redirect(url_for('contests.edit', id=contest.id))
                else:
                    error = gettext('contests.edit.atleastonegroup')
            else:
                error = gettext('contests.edit.emptyname')

    if contest is None:
        return render_template('errors/404.html'), 404

    contest_groups = Group.query.filter(Group.contests.any( \
        GroupContestAssociation.contest_id == contest.id))

    contest_groups_map = {}
    for group in contest_groups:
        contest_groups_map[group.id] = True

    for group in admin_groups:
        group.active = contest_groups_map.get(group.id, False)

    del contest_groups_map

    return render_template('contests/edit.html', contest=contest,
        error=error, contest_rulesets=contest_rulesets, admin_groups=admin_groups)

@mod.route('/<int:id>/delete')
@yield_contest()
@requires_admin(contest="contest")
def delete(id, contest):
    """Delete contest"""
    for x in ContestProblemAssociation.query.filter( \
        ContestProblemAssociation.contest_id == contest.id):
        db.session.delete(x)
    db.session.delete(contest)
    db.session.commit()
    return redirect(url_for('index'))

def format_time(mins):
    """Format time in minutes to match regex hh+:mm"""
    if mins is None:
        return ''
    hour = mins // 60
    mins = mins % 60
    return ("0" * (hour < 10) + str(hour)) + ':' + \
           ("0" * (mins < 10) + str(mins))

@mod.route('/<int:id>/scoreboard')
@yield_contest()
def scoreboard(id, contest):
    """Return scoreboard"""
    cache_name = '/contests/scoreboard/%d/%r' % (contest.id, g.user.is_admin(contest=contest))
    rawscore = cache.get(cache_name)
    if rawscore is None:
        problems = contest.problems
        users = []
        for user in User.query:
            score = contest.rate_user(user)
            solved_map = {}
            add_user = False
            for problem in problems:
                succeed, submitted = problem.user_succeed(user, freeze=contest.get_freeze_time())
                time = None
                if submitted is not None:
                    time = int(max(0, (submitted - contest.start).total_seconds() // 60))
                    add_user = True
                solved_map[problem.id] = {
                    "succeed": succeed,
                    "time": format_time(time),
                    "failed": problem.get_user_failed_attempts(user, freeze=contest.get_freeze_time())
                }
            if add_user:
                users.append({
                    "id": user.id,
                    "score": score,
                    "username": user.username,
                    "is_solved": solved_map
                })
        if contest.rules == 'acm':
            users.sort(key=lambda x:(-x['score'][0], x['score'][1]))
        else:
            users.sort(key=lambda x:(-x['score'][0]))

        rawscore = (render_template('contests/raw_scoreboard.html',
            contest=contest, problems=problems, users=users), g.now)
        cache.set(cache_name, rawscore, timeout=g.SETTINGS.get('scoreboard_cache_timeout', 60))
    if request.args.get('printing'):
        return render_template('contests/printing_scoreboard.html',
            scoreboard=rawscore[0])
    return render_template('contests/scoreboard.html',
        scoreboard=rawscore[0], contest=contest, updated=rawscore[1])

@mod.route('/list')
def list():
    """List active contests"""
    contests = Contest.query.all()
    raw = render_template('contests/rawlist.html', contests=contests)
    return render_template('contests/list.html', rawlist=raw)