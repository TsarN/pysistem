# -*- coding: utf-8 -*-
from pysistem import app, babel, redirect_url
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint
from pysistem.conf import LANGUAGES
from flask_babel import gettext

mod = Blueprint('locale', __name__, url_prefix='/locale')

@mod.route('/set/<lang>')
def set(lang):
    for i in LANGUAGES.keys():
        if lang == i:
            session['language'] = lang
            flash(gettext('locale.set.success', lang=LANGUAGES[lang]))
            return redirect(redirect_url())
    flash('::danger ' + gettext('locale.set.langnotfound', lang=lang))
    return redirect(redirect_url())
