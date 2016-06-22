# -*- coding: utf-8 -*-

"""Configuration management commands"""

import os
from flask_script import Manager
from pysistem import manager, basedir

ConfigCommand = Manager(usage='Edit PySistem configuration')

@ConfigCommand.command
def default():
    """Copy default configuration file"""
    from shutil import copyfile
    copyfile(os.path.join(basedir, 'conf_default.py'), os.path.join(basedir, 'conf.py'))
    print("Default configuration copied")

@ConfigCommand.option('-l', '--length', dest='length', default=24,
                      help="Length of key to generate. Default is 24")

def gensecret(length=24):
    """Generate new secret key and save it into configuration file"""
    with open(os.path.join(basedir, 'conf.py'), "r") as file:
        config = file.read()
    import re
    regex = re.compile('^[ \t\r\n]*SECRET_KEY')
    replacement = 'SECRET_KEY = ' + str(os.urandom(length))
    new_config = '\n'.join([replacement if regex.match(x) else x for x in config.split('\n')])

    with open(os.path.join(basedir, 'conf.py'), "w") as file:
        file.write(new_config)
    print("Secret key generated")

manager.add_command('config', ConfigCommand)
