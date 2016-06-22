# -*- coding: utf-8 -*-
from pysistem import db
from flask import render_template, g, flash, redirect, url_for, request, Blueprint
from flask_babel import gettext
from pysistem.lessons.model import Lesson, LessonUserAssociation, AutoMark
from pysistem.lessons.decorators import yield_lesson
from pysistem.groups.decorators import yield_group
from pysistem.users.decorators import requires_admin
from pysistem.groups.model import Group, GroupUserAssociation
from pysistem.contests.model import Contest
from datetime import datetime

mod = Blueprint('lessons', __name__, url_prefix='/lesson')

@mod.route('/<int:lesson_id>/delete')
@yield_lesson()
@requires_admin(lesson="lesson")
def delete(lesson_id, lesson):
    """Delete a lesson"""
    group_id = lesson.group_id
    db.session.delete(lesson)
    db.session.commit()
    flash(gettext('lessons.delete.success'))
    return redirect(url_for('groups.lessons', group_id=group_id))

@mod.route('/<int:group_id>/new', methods=['GET'])
@yield_group(field="group_id")
@requires_admin(group="group")
def new(group_id, group):
    """Create a lesson"""
    return render_template('lessons/edit.html', lesson=Lesson(), group=group)


@mod.route('/<int:lesson_id>/edit', methods=['GET', 'POST'])
@mod.route('/<int:group_id>/new', methods=['POST'])
def edit(lesson_id=-1, group_id=-1):
    """Update a lesson"""
    error = None
    group = None
    lesson = Lesson.query.get(lesson_id)
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

        contest = None
        contest_id = request.form.get('contest_id', "none")
        if contest_id != "none":
            try:
                contest_id = int(contest_id)
            except: pass

            contest = Contest.query.get(contest_id)

            if not contest:
                return render_template('errors/404.html'), 404

        if start <= end:
            if len(name.strip(' \t\n\r')) > 0:
                lesson.name = name
                lesson.start = start
                lesson.end = end
                db.session.add(lesson)
                changed_contest = False
                if contest:
                    if lesson.contest_id != contest.id:
                        changed_contest = True
                        if lesson.auto_marks:
                            for auto_mark in lesson.auto_marks:
                                db.session.delete(auto_mark)
                    lesson.contest_id = contest.id
                else:
                    lesson.contest_id = None

                if is_new:
                    lesson.group_id = group.id

                db.session.commit()

                if not is_new:
                    # Updating attendance, marks and auto marks
                    users = GroupUserAssociation.query.filter(db.and_(
                        GroupUserAssociation.group_id == lesson.group_id,
                        GroupUserAssociation.role == 'user'))

                    for user in users:
                        attendance = bool(request.form.get('user-was-%d' % user.id))
                        mark = request.form.get('user-mark-%d' % user.id)

                        assoc = LessonUserAssociation.query.filter(db.and_(
                            LessonUserAssociation.lesson_id == lesson.id,
                            LessonUserAssociation.user_id == user.id)).first()

                        if assoc:
                            assoc.mark = mark

                        if attendance and not assoc:
                            assoc = LessonUserAssociation()
                            assoc.lesson_id = lesson.id
                            assoc.user_id = user.id
                            assoc.mark = mark
                            db.session.add(assoc)
                        if not attendance and assoc:
                            db.session.delete(assoc)

                    if not changed_contest:
                        for auto_mark in lesson.auto_marks:
                            do_delete = bool(request.form.get('am%d-delete' % auto_mark.id))
                            if do_delete:
                                db.session.delete(auto_mark)
                                continue
                            required = request.form.get('am%d-required' % auto_mark.id, '')
                            mark = request.form.get('am%d-mark' % auto_mark.id, '')
                            points = request.form.get('am%d-points' % auto_mark.id, '')

                            try:
                                auto_mark.required = int(required)
                                auto_mark.mark = mark
                                auto_mark.points = int(points)
                            except ValueError:
                                pass

                            db.session.add(auto_mark)

                        for typ in ("score", "place", "solved"):
                            idx = 0
                            while True:
                                idx += 1
                                avail = request.form.get('am-new%s%d-avail' % (typ, idx), False)
                                if not avail:
                                    break
                                required = request.form.get('am-new%s%d-required' % (typ, idx))
                                mark = request.form.get('am-new%s%d-mark' % (typ, idx))
                                points = request.form.get('am-new%s%d-points' % (typ, idx))
                                try:
                                    required = int(required)
                                    points = int(points)
                                except:
                                    continue

                                m = AutoMark(type=typ, required=required, mark=mark, points=points)
                                m.lesson_id = lesson.id
                                db.session.add(m)

                    db.session.commit()
                if is_new:
                    flash(gettext('lessons.new.success'))
                else:
                    flash(gettext('lessons.edit.success'))
                return redirect(url_for('lessons.edit', lesson_id=lesson.id))
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

    marked_users = {}
    for assoc in lesson.users:
        marked_users[assoc.user.id] = assoc.mark or True

    users = [x for x in lesson.group.users if x.role == 'user']
    for user in users:
        user.mark = marked_users.get(user.id)

    users.sort(key=lambda x:x.last_name + ' ' + x.first_name)

    contests = [x for x in Contest.query if g.user.is_admin(contest=x)]

    return render_template('lessons/edit.html', lesson=lesson,
        error=error, group=group, users=users, contests=contests)