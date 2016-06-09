# -*- coding: utf-8 -*-
from pysistem import app, babel, db, redirect_url
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from pysistem.submissions.model import Submission
from pysistem.users.decorators import requires_admin
from pysistem.submissions.decorators import yield_submission
from pysistem.submissions.const import *

mod = Blueprint('submissions', __name__, url_prefix='/submission')

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

@mod.route('/<int:id>/checklog')
@yield_submission()
@requires_admin(submission="submission")
def checklog(id, submission):
    return Response(submission.check_log, mimetype='text/plain')

@mod.route('/<int:id>/recheck')
@yield_submission()
@requires_admin(submission="submission")
def recheck(id, submission):
    submission.status = STATUS_CWAIT
    db.session.commit()
    submission.async_check()
    return redirect(redirect_url())

@mod.route('/<int:id>/reject')
@yield_submission()
@requires_admin(submission="submission")
def reject(id, submission):
    submission.result = RESULT_RJ
    submission.status = STATUS_DONE
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
        submission.async_check()
    return redirect(redirect_url())

@mod.route('/reject/<int_list:ids>')
@requires_admin
def reject_all(ids):
    subs = Submission.query.filter(Submission.id.in_(ids))
    for submission in subs:
        submission.result = RESULT_RJ
        submission.status = STATUS_DONE
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