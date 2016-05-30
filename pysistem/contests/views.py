from pysistem import app, babel, db
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint
from flask_babel import gettext
from pysistem.contests.model import Contest

mod = Blueprint('contests', __name__, url_prefix='/contest')

@mod.route('/list')
def list():
    return render_template('contests/list.html', contests=Contest.query.all())

@mod.route('/ctl/<id>')
def ctl(id):
    contest = Contest.query.get(id) or Contest()
    return render_template('contests/ctl.html', contest=contest)