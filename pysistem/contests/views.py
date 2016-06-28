# -*- coding: utf-8 -*-

"""Contest views"""

from datetime import datetime

from flask import render_template, g, flash, redirect, url_for, request, Blueprint
from flask_babel import gettext

from pysistem import db, redirect_url, cache
from pysistem.contests.model import Contest, ContestProblemAssociation, contest_rulesets
from pysistem.submissions.model import Submission
from pysistem.users.model import User
from pysistem.problems.model import Problem
from pysistem.users.decorators import requires_admin
from pysistem.contests.decorators import yield_contest
from pysistem.problems.decorators import yield_problem
from pysistem.groups.model import Group, GroupContestAssociation, GroupUserAssociation

mod = Blueprint('contests', __name__, url_prefix='/contest')

@mod.route('/<int:contest_id>/linkwith/<int:problem_id>')
@yield_contest()
@yield_problem(field='problem_id')
@requires_admin(contest="contest")
@requires_admin(problem="problem")
def linkwith(contest_id, problem_id, contest, problem):
    """Add problem to contest

    ROUTE arguments:
    contest_id -- Contest's ID
    problem_id -- Problem's ID

    Permissions required:
    Contest Administrator
    Problem Administrator
    """
    assoc = ContestProblemAssociation()
    assoc.contest = contest
    assoc.problem = problem
    contest.problems.append(assoc)
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/<int:contest_id>/unlinkwith/<int:problem_id>')
@yield_contest()
@requires_admin(contest="contest")
@yield_problem(field='problem_id')
def unlinkwith(contest_id, problem_id, contest, problem):
    """Remove problem from contest

    ROUTE arguments:
    contest_id -- Contest's ID
    problem_id -- Problem's ID

    Permissions required:
    Contest Administrator
    """
    assoc = ContestProblemAssociation.query.filter(db.and_(
        ContestProblemAssociation.contest_id == contest_id,
        ContestProblemAssociation.problem_id == problem_id)).first()
    db.session.delete(assoc)
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/<int:contest_id>/problemprefix/<int:problem_id>', methods=['GET', 'POST'])
@yield_contest()
@requires_admin(contest="contest_id")
@yield_problem(field="problem_id")
def problemprefix(contest_id, problem_id, contest, problem):
    """Update problem prefix in contest

    ROUTE arguments:
    contest_id -- Contest's ID
    problem_id -- Problem's ID

    GET/POST arguments:
    prefix -- Problem's new prefix

    Permissions required:
    Contest Administrator
    """
    assoc = ContestProblemAssociation.query.filter(db.and_(
        ContestProblemAssociation.contest_id == contest_id,
        ContestProblemAssociation.problem_id == problem_id)).first()
    if not assoc:
        return render_template('errors/404.html'), 404
    assoc.prefix = request.values.get('prefix', assoc.prefix)
    db.session.commit()
    if request.method == 'POST':
        return 'success'
    else:
        return redirect(redirect_url())

@mod.route('/<int:contest_id>')
@yield_contest()
def problems(contest_id, contest):
    """Show contest's problems

    ROUTE arguments:
    contest_id -- Contest's ID

    Permissions required:
    None
    """
    addable_problems = Problem.query.all()
    if g.user.is_admin(contest=contest) and (contest.problems.count() > 0):
        addable_problems = \
        Problem.query.filter(~Problem.id.in_([x.id for x in contest.problems])).all()
        addable_problems = [x for x in addable_problems if g.user.is_admin(problem=x)]
    return render_template('contests/problems.html', contest=contest,
                           addable_problems=addable_problems)

@mod.route('/new')
def new():
    """Create new contest

    GET arguments:
    [group_id] -- group to add contest to

    Permissions required:
    Server Administrator (if not GET.group_id)
    Group Administrator (if GET.group_id)
    """
    group_id = request.args.get('group_id')
    group = None
    if not group_id and not g.user.is_admin():
        return render_template('errors/403.html'), 403
    elif group_id:
        group = Group.query.get(group_id)
        if not group:
            return render_template('errors/404.html'), 404
        if not g.user.is_admin(group=group):
            return render_template('errors/403.html'), 403

    return render_template('contests/edit.html', contest=Contest(),
                           contest_rulesets=contest_rulesets, group=group)

@mod.route('/<int:contest_id>/edit', methods=['GET', 'POST'])
@mod.route('/new', methods=['POST'])
def edit(contest_id=-1):
    """Create/Update contest

    ROUTE arguments:
    [contest_id] -- Contest's ID

    Permissions required (Update):
    Contest Administrator

    Permissions required (Create):
    Server Administrator (if not group_id)
    Group Administrator (if group_id)
    """
    contest = Contest.query.get(contest_id)
    error = None

    if contest:
        if not g.user.is_admin(contest=contest):
            return render_template('errors/403.html'), 403

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
        try:
            start = datetime.strptime(request.form.get('start', g.now_formatted), "%Y-%m-%d %H:%M")
            end = datetime.strptime(request.form.get('end', g.now_formatted), "%Y-%m-%d %H:%M")
            freeze = datetime.strptime(request.form.get('freeze', g.now_formatted), "%Y-%m-%d %H:%M")
        except ValueError:
            error = gettext('error.invaliddateformat')
        if not error:
            unfreeze_after_end = bool(request.form.get('unfreeze_after_end', False))
            rules = request.form.get('ruleset', 'acm')

            group_test = any([g.user.is_admin()] + \
                [bool(request.form.get('group-%d' % group.id, False)) \
                for group in admin_groups])

            group_id = request.form.get('group_id')
            try:
                group_id = int(group_id)
            except: pass
            group = None
            if is_new:
                if not group_id and not g.user.is_admin():
                    return render_template('errors/403.html'), 403
                elif group_id:
                    group = Group.query.get(group_id)
                    if not group:
                        return render_template('errors/404.html'), 404
                    if not g.user.is_admin(group=group_id):
                        return render_template('errors/403.html'), 403
                    group_test = True

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
                            if group:
                                assoc = GroupContestAssociation()
                                assoc.group_id = group.id
                                assoc.contest = contest
                                db.session.add(assoc)

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
                            return redirect(url_for('contests.problems', contest_id=contest.id))
                        else:
                            flash(gettext('contests.edit.success'))
                            return redirect(url_for('contests.edit', contest_id=contest.id))
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
                           error=error, contest_rulesets=contest_rulesets,
                           admin_groups=admin_groups)

@mod.route('/<int:contest_id>/delete')
@yield_contest()
@requires_admin(contest="contest")
def delete(contest_id, contest):
    """Delete contest

    ROUTE arguments:
    contest_id -- Contest's ID

    Permissions required:
    Contest Administrator
    """
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


def render_scoreboard(contest, cache_name):
    """Do actual scoreboard rendering"""
    if contest.problems.count() == 0:
        submissions = []
        problems = []
        qusers = []
    else:
        problem_ids = [x.id for x in contest.problems]
        submissions = Submission.query.filter(Submission.problem_id.in_(problem_ids))
        problems = [x.problem for x in submissions.distinct(Submission.problem_id)
                                                  .group_by(Submission.problem_id)]
        qusers = [x.user for x in submissions.distinct(Submission.user_id)
                                             .group_by(Submission.user_id)]
    subs = {}
    for user in qusers:
        subs[user.id] = {}
        for problem in problems:
            subs[user.id][problem.id] = []

    for sub in submissions:
        subs[sub.user_id][sub.problem_id].append(sub)

    users = []

    for user in qusers:
        score = contest.rate_user(user, subs=subs[user.id])
        solved_map = {}
        add_user = False
        for problem in problems:
            succeed, submitted = problem.user_score(user, freeze=contest.get_freeze_time(),
                                                    subs=subs[user.id][problem.id])
            if contest.rules == 'acm':
                succeed = bool(succeed) and (problem.get_max_score() <= succeed)
            time = None
            if submitted is not None:
                time = int(max(0, (submitted - contest.start).total_seconds() // 60))
                add_user = True
            solved_map[problem.id] = {
                "succeed": succeed,
                "time": format_time(time),
                "failed": problem.get_user_failed_attempts(user, subs=subs[user.id][problem.id],
                                                           freeze=contest.get_freeze_time())
            }
        if add_user:
            users.append({
                "id": user.id,
                "score": score,
                "username": user.username,
                "is_solved": solved_map
            })
    if contest.rules == 'acm':
        users.sort(key=lambda x: (-x['score'][0], x['score'][1]))
    else:
        users.sort(key=lambda x: (-x['score'][0]))

    # Calculating fair places
    if users:
        last_idx = 0
        cur_place = 1
        cur_score = users[0]['score']
        users[0]['place'] = '1'
        users[0]['int_place'] = 1

        for i in range(1, len(users)):
            if cur_score != users[i]['score']:
                cur_score = users[i]['score']
                cur_place = i + 1
                for j in range(i - 1, last_idx - 1, -1):
                    if i != users[j]['int_place']:
                        users[j]['place'] += '-' + str(i)
                last_idx = i
            users[i]['place'] = str(cur_place)
            users[i]['int_place'] = cur_place

        user_len = len(users)
        for j in range(user_len - 1, last_idx - 1, -1):
            if users[j]['int_place'] != user_len:
                users[j]['place'] += '-' + str(user_len)

    rawscore = (render_template('contests/raw_scoreboard.html',
                                contest=contest, problems=problems, users=users), g.now)
    cache.set(cache_name, rawscore, timeout=g.SETTINGS.get('scoreboard_cache_timeout', 60))
    return rawscore

@mod.route('/<int:contest_id>/scoreboard')
@yield_contest()
def scoreboard(contest_id, contest):
    """Show scoreboard

    ROUTE arguments:
    contest_id -- Contest's ID

    Permissions required:
    None
    """
    cache_name = '/contests/scoreboard/%d/%r' % (contest.id, g.user.is_admin(contest=contest))
    rawscore = cache.get(cache_name)
    if rawscore is None:
        rawscore = render_scoreboard(contest, cache_name)

    if request.args.get('printing'):
        return render_template('contests/printing_scoreboard.html',
                               scoreboard=rawscore[0])
    return render_template('contests/scoreboard.html',
                           scoreboard=rawscore[0], contest=contest, updated=rawscore[1])

@mod.route('/list', endpoint="list")
def listcontests():
    """List active contests

    Permissions required:
    None
    """
    contests = Contest.query.all()
    contests_data = dict([(x.id, (x.start, x.end)) for x in contests])
    raw = render_template('contests/rawlist.html', contests=contests, contests_data=contests_data)
    return render_template('contests/list.html', rawlist=raw)
