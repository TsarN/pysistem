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
    if (g.user.role != 'admin') and (submission.user_id != g.user.id):
        return render_template('errors/403.html'), 403
    return Response(submission.source, mimetype='text/plain')

@mod.route('/<int:id>/compilelog')
@yield_submission()
def compilelog(id, submission):
    if (g.user.role != 'admin') and \
        ((submission.user_id != g.user.id) or not submission.is_compile_failed()):
        return render_template('errors/403.html'), 403
    return Response(submission.compile_log, mimetype='text/plain')

@mod.route('/<int:id>/checklog')
@requires_admin
@yield_submission()
def checklog(id, submission):
    return Response(submission.check_log, mimetype='text/plain')

@mod.route('/<int:id>/recheck')
@requires_admin
@yield_submission()
def recheck(id, submission):
    submission.status = STATUS_CWAIT
    db.session.commit()
    submission.async_check()
    return redirect(redirect_url())

@mod.route('/<int:id>/reject')
@requires_admin
@yield_submission()
def reject(id, submission):
    submission.result = RESULT_RJ
    submission.status = STATUS_DONE
    db.session.commit()
    return redirect(redirect_url())

@mod.route('/<int:id>/delete')
@requires_admin
@yield_submission()
def delete(id, submission):
    db.session.delete(submission)
    db.session.commit()
    return redirect(redirect_url())