from pysistem import app, babel, db
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from pysistem.submissions.model import Submission
from pysistem.users.decorators import requires_admin

mod = Blueprint('submissions', __name__, url_prefix='/submission')

@mod.route('/<int:id>/source')
def source(id):
    sub = Submission.query.get(id)
    if sub is None:
        return render_template('errors/404.html'), 404
    if (g.user.role != 'admin') and (sub.user_id != g.user.id):
        return render_template('errors/403.html'), 403
    return Response(sub.source, mimetype='text/plain')

@mod.route('/<int:id>/compilelog')
def compilelog(id):
    sub = Submission.query.get(id)
    if sub is None:
        return render_template('errors/404.html'), 404
    if (g.user.role != 'admin') and \
        ((sub.user_id != g.user.id) or not sub.is_compile_failed()):
        return render_template('errors/403.html'), 403
    return Response(sub.compile_log, mimetype='text/plain')

@mod.route('/<int:id>/checklog')
@requires_admin
def checklog(id):
    sub = Submission.query.get(id)
    if sub is None:
        return render_template('errors/404.html'), 404
    return Response(sub.check_log, mimetype='text/plain')