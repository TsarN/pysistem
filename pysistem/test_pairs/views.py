# -*- coding: utf-8 -*-
from pysistem import app, babel, db, redirect_url
from flask import render_template, session, g, flash, redirect, url_for, request, Blueprint, Response
from pysistem.users.decorators import requires_admin
from pysistem.test_pairs.model import TestPair
from pysistem.test_pairs.decorators import yield_test_pair

mod = Blueprint('test_pairs', __name__, url_prefix='/testpair')

@mod.route('/<int:id>/input')
@yield_test_pair()
@requires_admin(test_pair="test")
def view_input(id, test):
    return Response(test.input, mimetype='text/plain')

@mod.route('/<int:id>/pattern')
@yield_test_pair()
@requires_admin(test_pair="test")
def view_pattern(id, test):
    return Response(test.pattern, mimetype='text/plain')