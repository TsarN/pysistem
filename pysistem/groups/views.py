# -*- coding: utf-8 -*-

"""Group-related views"""

from flask import render_template, flash, redirect, request, Blueprint
from flask_babel import gettext

from pysistem.groups.decorators import yield_group, requires_group_membership
from pysistem.users.decorators import requires_admin
from pysistem.groups.model import Group
from pysistem import db, redirect_url

mod = Blueprint('groups', __name__, url_prefix='/group')

@mod.route('/<int:group_id>/users')
@yield_group()
@requires_admin(group="group")
def users(group_id, group):
    """Show group's users

    ROUTE parameters:
    group_id -- Group's ID

    Permissions required:
    Group Administrator
    """
    return render_template('groups/users.html', group=group, users=group.users)

@mod.route('/<int:group_id>/contests')
@yield_group()
@requires_group_membership()
def contests(group_id, group):
    """Show group's contests

    ROUTE parameters:
    group_id -- Group's ID

    Permissions required:
    Group Member
    """
    raw = render_template('contests/rawlist.html', contests=group.contests)
    return render_template('groups/contests.html', group=group, rawlist=raw)

@mod.route('/<int:group_id>/lessons')
@yield_group()
@requires_admin(group="group")
def lessons(group_id, group):
    """Show group's lessons

    ROUTE parameters:
    group_id -- Group's ID

    Permissions required:
    Group Administrator
    """
    return render_template('groups/lessons.html', group=group)

@mod.route('/create', methods=['POST'])
@requires_admin()
def create():
    """Create group

    POST parameters:
    name -- Group's name. Must not be empty

    Permissions required:
    Server Administrator
    """
    name = request.form.get('name', '')
    if len(name) < 1:
        flash('::danger ' + gettext('groups.edit.emptyname'))
    else:
        db.session.add(Group(name=name))
        db.session.commit()
        flash(gettext('groups.create.success'))
    return redirect(redirect_url())

@mod.route('/rename/<int:group_id>', methods=['POST'])
@yield_group()
@requires_admin(group="group")
def rename(group_id, group):
    """Rename group

    ROUTE parameters:
    group_id -- Group ID to rename

    POST parameters:
    name -- Group's new name. Must not be empty

    Permissions required:
    Group Administrator
    """

    name = request.form.get('name', '')
    if len(name) < 1:
        flash('::danger ' + gettext('groups.edit.emptyname'))
    else:
        group.name = name
        db.session.commit()
        flash(gettext('groups.rename.success'))
    return redirect(redirect_url())
