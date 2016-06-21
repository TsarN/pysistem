# -*- coding: utf-8 -*-
from pysistem import manager
from pysistem.commands import *
import sys
try:
    result = manager.handle('', sys.argv[1:])
except SystemExit as e:
    result = e.code
sys.exit(result or 0)