# -*- coding: utf-8 -*-
from pysistem import app, db
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from pysistem.groups.decorators import yield_group, requires_group_membership
from pysistem.users.decorators import requires_admin
from pysistem.lessons.model import Lesson

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