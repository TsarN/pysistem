# -*- coding: utf-8 -*-
from pysistem import app, babel, db, redirect_url, cache
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from pysistem.submissions.model import Submission, SubmissionLog
from pysistem.users.decorators import requires_admin
from pysistem.submissions.decorators import yield_submission
from pysistem.test_pairs.model import TestGroup
from pysistem.submissions.const import *

mod = Blueprint('submissions', __name__, url_prefix='/submission')

@mod.route('/<int:id>')
@yield_submission()
def view(id, submission):
    if not g.user.is_admin(submission=submission) and (submission.user_id != g.user.id):
        return render_template('errors/403.html'), 403
    cache_name = '/submission/view/%d/%r' % (id, g.user.is_admin(submission=submission))
    rawview = cache.get(cache_name)
    if rawview is None:
        submission_logs = SubmissionLog.query.filter( \
            SubmissionLog.submission_id == submission.id).all()

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
            try:
                from pysistem.test_pairs.model import TestPair
                test_pair = TestPair.query.get(submission.current_test_id)
                logs[test_pair.test_group_id].append({
                    "result": RESULT_UNKNOWN,
                    "log": "",
                    "stdout": "",
                    "input": test_pair.input,
                    "pattern": test_pair.pattern,
                    "id": test_pair.id,
                    "score": 0
                })
            except: pass
        for x in logs:
            logs[x].sort(key=lambda q: q['id'])

        logs_list = []
        for x in sorted(logs.keys()):
            logs_list.append({
                "tests": logs[x],
                "groupscore": TestGroup.query.get(x).score if \
                all(map(lambda y: y['result'] == RESULT_OK, logs[x])) \
                else 0,
                "totalscore": (TestGroup.query.get(x).score if \
                all(map(lambda y: y['result'] == RESULT_OK, logs[x])) \
                else 0) + sum(map(lambda y: y['score'], logs[x]))
            })

        rendered_sub = render_template('submissions/list.html', submissions=[submission],
            show_user=True, show_problem=True, disable_all_actions=True, hide_source=True)

        rawview = render_template('submissions/rawview.html', submission=submission,
            logs=logs_list, rendered_sub=rendered_sub)
        if submission.status in [STATUS_DONE, STATUS_ACT]:
            cache.set(cache_name, rawview)
    return render_template('submissions/view.html', rawview=rawview, id=submission.id)

@mod.route('/<int:id>/source')
@yield_submission()
def source(id, submission):
    if not g.user.is_admin(submission=submission) and (submission.user_id != g.user.id):
        return render_template('errors/403.html'), 403
    return Response(submission.source, mimetype='text/plain')

@mod.route('/<int:id>/compilelog')
@yield_submission()
def compilelog(id, submission):
    if not g.user.is_admin(submission=submission) and \
        ((submission.user_id != g.user.id) or not submission.is_compile_failed()):
        return render_template('errors/403.html'), 403
    return Response(submission.compile_log, mimetype='text/plain')

@mod.route('/<int:id>/recheck')
@yield_submission()
@requires_admin(submission="submission")
def recheck(id, submission):
    submission.status = STATUS_CWAIT
    submission.current_test_id = 0
    db.session.commit()
    submission.async_check(force=True)
    return redirect(redirect_url())

@mod.route('/<int:id>/reject')
@yield_submission()
@requires_admin(submission="submission")
def reject(id, submission):
    submission.result = RESULT_RJ
    submission.status = STATUS_DONE
    submission.score = 0
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/<int:id>/delete')
@yield_submission()
@requires_admin(submission="submission")
def delete(id, submission):
    db.session.delete(submission)
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/recheck/<int_list:ids>')
@requires_admin
def recheck_all(ids):
    subs = Submission.query.filter(Submission.id.in_(ids))
    for submission in subs:
        submission.status = STATUS_CWAIT
        db.session.commit()
        submission.async_check(force=True)
    return redirect(redirect_url())

@mod.route('/reject/<int_list:ids>')
@requires_admin
def reject_all(ids):
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
    subs = Submission.query.filter(Submission.id.in_(ids))
    for submission in subs:
        db.session.delete(submission)
    db.session.commit()
    return redirect(redirect_url())