# -*- coding: utf-8 -*-
from pysistem import app, db
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from flask_babel import gettext
from pysistem.lessons.model import Lesson
from pysistem.lessons.decorators import yield_lesson
from pysistem.groups.decorators import yield_group
from pysistem.users.decorators import requires_admin
from pysistem.groups.model import Group
from datetime import datetime

mod = Blueprint('lessons', __name__, url_prefix='/lesson')

@mod.route('/<int:id>/delete')
@yield_lesson()
@requires_admin(lesson="lesson")
def delete(id, lesson):
    group_id = lesson.group_id
    db.session.delete(lesson)
    db.session.commit()
    flash(gettext('lessons.delete.success'))
    return redirect(url_for('groups.lessons', id=group_id))

@mod.route('/<int:group_id>/new', methods=['GET'])
@yield_group(field="group_id")
@requires_admin(group="group")
def new(group_id, group):
    return render_template('lessons/edit.html', lesson=Lesson(), group=group)


@mod.route('/<int:id>/edit', methods=['GET', 'POST'])
@mod.route('/<int:group_id>/new', methods=['POST'])
def edit(id=-1, group_id=-1):
    error = None
    group = None
    lesson = Lesson.query.get(id)
    if not lesson:
        if not g.user.is_admin(group=group_id):
            return render_template('errors/403.html'), 403
    else:
        if not g.user.is_admin(lesson=lesson):
            return render_template('errors/403.html'), 403
    if request.method == 'POST':
        lesson = lesson or Lesson()
        is_new = lesson.id is None

        if is_new:
            group = Group.query.get(group_id)
            if group is None:
                return render_template('errors/404.html'), 404

        name = request.form.get('name', '')
        start = datetime.strptime(request.form.get('start', g.now_formatted), "%Y-%m-%d %H:%M")
        end = datetime.strptime(request.form.get('end', g.now_formatted), "%Y-%m-%d %H:%M")

        if start <= end:
            if len(name.strip(' \t\n\r')) > 0:
                lesson.name = name
                lesson.start = start
                lesson.end = end

                if is_new:
                    lesson.group_id = group.id
                    db.session.add(lesson)

                db.session.commit()
                if is_new:
                    flash(gettext('lessons.new.success'))
                else:
                    flash(gettext('lessons.edit.success'))
                return redirect(url_for('groups.lessons', id=lesson.group_id))
            else:
                error = gettext('lessons.edit.emptyname')
        else:
            error = gettext('lessons.edit.invaliddates')

        # An error occurred. Save form data for displaing
        if is_new:
            lesson.name = name
            lesson.start = start
            lesson.end = end
    else:
        if lesson is None:
            return render_template('errors/404.html'), 404

    group = group or lesson.group

    return render_template('lessons/edit.html', lesson=lesson, error=error, group=group)