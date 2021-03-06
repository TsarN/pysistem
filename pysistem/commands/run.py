# -*- coding: utf-8 -*-

"""Commands for running PySistem"""

import sys
import logging
from time import sleep
import threading

from flask_script import Manager, Command, Option
from flask import _request_ctx_stack

try:
    from gunicorn import version_info
    enable_gunicorn = True
except ImportError:
    enable_gunicorn = False

from pysistem import app, manager

RunCommand = Manager(usage="Start PySistem services")

@RunCommand.option('-h', '--host', dest='host', default='127.0.0.1', help="Server host")
@RunCommand.option('-p', '--port', type=int, dest='port', default=5000, help="Server port")
@RunCommand.option('--threaded', dest='threaded', action='store_true',
                   default=False, help="Handle each request in separate thread")
@RunCommand.option('-d', '--debug', dest='debug', action='store_true', 
                   default=None, help='enable the Werkzeug debugger')
@RunCommand.option('-D', '--no-debug', dest='debug', action='store_false', 
                   default=None, help='disable the Werkzeug debugger')

def wsgi(**kwargs):
    """Run the app within Werkzeug"""
    return app.run(**kwargs)

@RunCommand.command
def checker(**kwargs):
    """Run checker thread"""
    app.start_check_thread(join=True)

@RunCommand.command
def tests(**kwargs):
    """Run PySistem test suite"""
    from pysistem.tests import TestCase
    import unittest
    import sys
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCase)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(len(result.failures))

@RunCommand.command
def shell():
    """Run interactive PySistem shell"""
    import pysistem.models
    import code
    modules = ('checkers', 'compilers', 'contests', 'problems', 'users',
               'submissions', 'test_pairs', 'groups', 'lessons', 'settings')

    context = dict(app=_request_ctx_stack.top.app)

    for module in modules:
        mod = getattr(__import__('pysistem.%s.model' % module), module).model
        for obj in dir(mod):
            if not obj.startswith('_'):
                context[obj] = getattr(mod, obj)

    # Try IPython
    try:
        try:
            # 0.10.x
            from IPython.Shell import IPShellEmbed
            ipshell = IPShellEmbed()
            ipshell(global_ns=dict(), local_ns=context, colors='Linux')
        except ImportError:
            # 0.12+
            from IPython import embed
            embed(user_ns=context, colors='Linux')
        return
    except ImportError:
        pass

    code.interact(local=context)

if enable_gunicorn:
    class GunicornServer(Command):
        """Run the app within Gunicorn"""

        def __init__(self, host='127.0.0.1', port=8000, workers=4):
            self.port = port
            self.host = host
            self.workers = workers
            Command.__init__(self)

        def get_options(self):
            return (
                Option('-H', '--host',
                       dest='host',
                       default=self.host),

                Option('-p', '--port',
                       dest='port',
                       type=int,
                       default=self.port),

                Option('-w', '--workers',
                       dest='workers',
                       type=int,
                       default=self.workers)
            )

        def run(self, host=None, port=None, workers=None):
            if version_info < (0, 9, 0):
                from gunicorn.arbiter import Arbiter
                from gunicorn.config import Config
                arbiter = Arbiter(Config({'bind': "%s:%d" % (host, int(port)),'workers': workers}), app)
                arbiter.run()
            else:
                from gunicorn.app.base import Application

                class FlaskApplication(Application):
                    def init(self, parser, opts, args):
                        return {
                            'bind': '{0}:{1}'.format(host, port),
                            'workers': workers
                        }

                    def load(self):
                        return app

                app.prerun()
                FlaskApplication().run()

    RunCommand.add_command('gunicorn', GunicornServer)

manager.add_command('run', RunCommand)
