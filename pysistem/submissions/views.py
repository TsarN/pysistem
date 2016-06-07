# -*- coding: utf-8 -*-
from pysistem import app, babel, db
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from pysistem.submissions.model import Submission
from pysistem.users.decorators import requires_admin
from pysistem.submissions.decorators import yield_submission

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
        ((sub.user_id != g.user.id) or not submission.is_compile_failed()):
        return render_template('errors/403.html'), 403
    return Response(submission.compile_log, mimetype='text/plain')

@mod.route('/<int:id>/checklog')
@requires_admin
@yield_submission()
def checklog(id, submission):
    return Response(submission.check_log, mimetype='text/plain')