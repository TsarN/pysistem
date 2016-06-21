# -*- coding: utf-8 -*-

from pysistem import app, manager
from flask_script import Manager, Command, Option

RunCommand = Manager(usage="Start PySistem services")

@RunCommand.option('-h', '--host', dest='host', default='127.0.0.1', help="Server host")
@RunCommand.option('-p', '--port', dest='port', default=5000, help="Server port")
@RunCommand.option('--threaded', dest='threaded', action='store_true',
    default=False, help="Should the process handle each request in separate thread?")
@RunCommand.option('-d', '--debug', dest='use_debugger', action='store_true', 
    default=None, help='enable the Werkzeug debugger (DO NOT use in production code)')
@RunCommand.option('-D', '--no-debug', dest='use_debugger', action='store_false', 
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

try:
    from gunicorn import version_info

    class GunicornServer(Command):
        """Run the app within Gunicorn"""

        def __init__(self, host='127.0.0.1', port=8000, workers=4):
            self.port = port
            self.host = host
            self.workers = workers

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

        def run(self, host, port, workers):
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

                FlaskApplication().run()

    RunCommand.add_command('gunicorn', GunicornServer)
except: pass

manager.add_command('run', RunCommand)