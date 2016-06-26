# -*- coding: utf-8 -*-

"""Submission views"""

from pysistem import db, redirect_url, cache
from flask import render_template, g, redirect, Blueprint, Response
from pysistem.submissions.model import Submission, SubmissionLog
from pysistem.users.decorators import requires_admin
from pysistem.submissions.decorators import yield_submission
from pysistem.test_pairs.model import TestGroup
from pysistem.submissions.const import STATUS_DONE, STATUS_CWAIT, STATUS_ACT
from pysistem.submissions.const import RESULT_OK, RESULT_UNKNOWN, RESULT_RJ

mod = Blueprint('submissions', __name__, url_prefix='/submission')

@mod.route('/<int:submission_id>')
@yield_submission()
def view(submission_id, submission):
    """View submission info

    ROUTE arguments:
    submission_id -- Submission's ID

    Permissions Required (Basic View):
    Submission owner

    Permissions Required (Advanced View):
    Submission Administrator

    """
    from pysistem.test_pairs.model import TestPair
    if not g.user.is_admin(submission=submission) and (submission.user_id != g.user.id):
        return render_template('errors/403.html'), 403
    cache_name = '/submission/view/%d/%r' % (submission_id, g.user.is_admin(submission=submission))
    rawview = cache.get(cache_name)
    if rawview is None:
        submission_logs = submission.submission_logs.all()

        logs = {}
        for sub in submission_logs:
            if sub.test_pair.test_group_id not in logs.keys():
                logs[sub.test_pair.test_group_id] = []
            logs[sub.test_pair.test_group_id].append({
                "result": sub.result,
                "log": sub.log,
                "stdout": sub.stdout,
                "input": sub.test_pair.input,
                "pattern": sub.test_pair.pattern,
                "id": sub.test_pair.id,
                "score": sub.test_pair.test_group.score_per_test if sub.result == RESULT_OK else 0
            })
        if submission.current_test_id > 0:
            test_pair = TestPair.query.get(submission.current_test_id)
            if test_pair and (test_pair.test_group_id in logs):
                logs[test_pair.test_group_id].append({
                    "result": RESULT_UNKNOWN,
                    "log": "",
                    "stdout": "",
                    "input": test_pair.input,
                    "pattern": test_pair.pattern,
                    "id": test_pair.id,
                    "score": 0
                })
        for log in logs:
            logs[log].sort(key=lambda q: q['id'])

        logs_list = []
        for x in sorted(logs.keys()):
            logs_list.append({
                "tests": logs[x],
                "groupscore": TestGroup.query.get(x).score if \
                all([y['result'] == RESULT_OK for y in logs[x]]) \
                else 0,
                "totalscore": (TestGroup.query.get(x).score if \
                all([y['result'] == RESULT_OK for y in logs[x]]) \
                else 0) + sum([y['score'] for y in logs[x]])
            })

        rendered_sub = render_template('submissions/list.html', submissions=[submission],
                                       show_user=True, show_problem=True,
                                       disable_all_actions=True, hide_source=True)

        rawview = render_template('submissions/rawview.html', submission=submission,
                                  logs=logs_list, rendered_sub=rendered_sub)
        if submission.status in [STATUS_DONE, STATUS_ACT]:
            cache.set(cache_name, rawview)
    return render_template('submissions/view.html', rawview=rawview, submission_id=submission.id)

@mod.route('/<int:submission_id>/source')
@yield_submission()
def source(submission_id, submission):
    """Download submission's source

    ROUTE arguments:
    submission_id -- Submission's ID

    Permissions Required (at least one):
    Submission owner
    Submission Administrator
    """
    if not g.user.is_admin(submission=submission) and (submission.user_id != g.user.id):
        return render_template('errors/403.html'), 403
    return Response(submission.source, mimetype='text/plain')

@mod.route('/<int:submission_id>/compilelog')
@yield_submission()
def compilelog(submission_id, submission):
    """Download submission's compilation log

    ROUTE arguments:
    submission_id -- Submission's ID

    Permissions Required (at least one):
    Submission owner (only if compilation failed)
    Submission Administrator
    """
    if not g.user.is_admin(submission=submission) and \
        ((submission.user_id != g.user.id) or not submission.is_compile_failed()):
        return render_template('errors/403.html'), 403
    return Response(submission.compile_log, mimetype='text/plain')

@mod.route('/<int:submission_id>/recheck')
@yield_submission()
@requires_admin(submission="submission")
def recheck(submission_id, submission):
    """Recheck a submission

    ROUTE arguments:
    submission_id -- Submission's ID

    Permissions Required:
    Submission Administrator
    """
    submission.status = STATUS_CWAIT
    submission.current_test_id = 0
    db.session.add(submission)
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/<int:submission_id>/reject')
@yield_submission()
@requires_admin(submission="submission")
def reject(submission_id, submission):
    """Reject a submission

    ROUTE arguments:
    submission_id -- Submission's ID

    Permissions Required:
    Submission Administrator
    """
    submission.result = RESULT_RJ
    submission.status = STATUS_DONE
    submission.score = 0
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/<int:submission_id>/delete')
@yield_submission()
@requires_admin(submission="submission")
def delete(submission_id, submission):
    """Delete a submission

    ROUTE arguments:
    submission_id -- Submission's ID

    Permissions Required:
    Submission Administrator
    """
    db.session.delete(submission)
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/recheck/<int_list:ids>')
@requires_admin
def recheck_all(ids):
    """Recheck list of submissions

    ROUTE arguments:
    submission_id -- Submission's ID

    Permissions Required:
    Server Administrator (TODO)
    """
    subs = Submission.query.filter(Submission.id.in_(ids))
    for submission in subs:
        submission.status = STATUS_CWAIT
        db.session.commit()
    return redirect(redirect_url())

@mod.route('/reject/<int_list:ids>')
@requires_admin
def reject_all(ids):
    """Reject list of submissions

    ROUTE arguments:
    submission_id -- Submission's ID

    Permissions Required:
    Server Administrator (TODO)
    """
    subs = Submission.query.filter(Submission.id.in_(ids))
    for submission in subs:
        submission.result = RESULT_RJ
        submission.status = STATUS_DONE
        submission.score = 0
        submission.current_test_id = 0
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/delete/<int_list:ids>')
@requires_admin
def delete_all(ids):
    """Delete list of submissions

    ROUTE arguments:
    submission_id -- Submission's ID

    Permissions Required:
    Server Administrator (TODO)
    """
    subs = Submission.query.filter(Submission.id.in_(ids))
    for submission in subs:
        db.session.delete(submission)
    db.session.commit()
    return redirect(redirect_url())
