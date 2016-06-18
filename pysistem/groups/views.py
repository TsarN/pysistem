# -*- coding: utf-8 -*-
from pysistem import app, db, redirect_url
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from pysistem.groups.decorators import yield_group, requires_group_membership
from pysistem.users.decorators import requires_admin
from pysistem.lessons.model import Lesson
from pysistem.groups.model import Group
from flask_babel import gettext

mod = Blueprint('groups', __name__, url_prefix='/group')

@mod.route('/<int:id>/users')
@yield_group()
@requires_admin(group="group")
def users(id, group):
    return render_template('groups/users.html', group=group, users=group.users)

@mod.route('/<int:id>/contests')
@yield_group()
@requires_group_membership()
def contests(id, group):
    raw = render_template('contests/rawlist.html', contests=group.contests)
    return render_template('groups/contests.html', group=group, rawlist=raw)

@mod.route('/<int:id>/lessons')
@yield_group()
@requires_admin(group="group")
def lessons(id, group):
    return render_template('groups/lessons.html', group=group)

@mod.route('/create', methods=['POST'])
@requires_admin()
def create():
    name = request.form.get('name', '')
    if len(name) < 1:
        flash('::danger ' + gettext('groups.edit.emptyname'))
    else:
        db.session.add(Group(name=name))
        db.session.commit()
        flash(gettext('groups.create.success'))
    return redirect(redirect_url())

@mod.route('/rename/<int:id>', methods=['POST'])
@yield_group()
@requires_admin(group="group")
def rename(id, group):
    name = request.form.get('name', '')
    if len(name) < 1:
        flash('::danger ' + gettext('groups.edit.emptyname'))
    else:
        group.name = name
        db.session.commit()
        flash(gettext('groups.rename.success'))
    return redirect(redirect_url())