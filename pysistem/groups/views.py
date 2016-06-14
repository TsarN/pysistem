# -*- coding: utf-8 -*-
from pysistem import app, db
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from pysistem.groups.decorators import yield_group
from pysistem.users.decorators import requires_admin

mod = Blueprint('groups', __name__, url_prefix='/group')

@mod.route('/<int:id>/users')
@yield_group()
@requires_admin(group="group")
def users(id, group):
    return render_template('groups/users.html', group=group, users=group.users)

@mod.route('/<int:id>/contests')
@yield_group()
def contests(id, group):
    raw = render_template('contests/rawlist.html', contests=group.contests)
    return render_template('groups/contests.html', group=group, rawlist=raw)