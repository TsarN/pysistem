# -*- coding: utf-8 -*-
from flask import Blueprint, Response
from pysistem.users.decorators import requires_admin
from pysistem.test_pairs.decorators import yield_test_pair

mod = Blueprint('test_pairs', __name__, url_prefix='/testpair')

@mod.route('/<int:test_pair_id>/input')
@yield_test_pair()
@requires_admin(test_pair="test")
def view_input(test_pair_id, test):
    """Download test pair input file

    ROUTE arguments:
    test_pair_id -- TestPair's ID

    Permissions required:
    TestPair Administrator
    """
    return Response(test.input, mimetype='text/plain')

@mod.route('/<int:test_pair_id>/pattern')
@yield_test_pair()
@requires_admin(test_pair="test")
def view_pattern(test_pair_id, test):
    """Download test pair pattern file

    ROUTE arguments:
    test_pair_id -- TestPair's ID

    Permissions required:
    TestPair Administrator
    """
    return Response(test.pattern, mimetype='text/plain')