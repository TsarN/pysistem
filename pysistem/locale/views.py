# -*- coding: utf-8 -*-
from flask import session, flash, redirect, Blueprint, render_template
from flask_babel import gettext
from pysistem import redirect_url

try:
    from pysistem.conf import LANGUAGES
except ImportError: # pragma: no cover
    from pysistem.conf_default import LANGUAGES

mod = Blueprint('locale', __name__, url_prefix='/locale')

@mod.route('/set/<lang>', endpoint='set')
def setlocale(lang):
    """Set current user's locale to lang

    Permissions required:
    None
    """
    for i in LANGUAGES.keys():
        if lang == i:
            session['language'] = lang
            flash(gettext('locale.set.success', lang=LANGUAGES[lang]))
            return redirect(redirect_url())
    return render_template('errors/404.html'), 404
