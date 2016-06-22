# -*- coding: utf-8 -*-
"""PySistem's __main__"""
import sys
from pysistem import manager
import pysistem.commands

def main():
    """Start manager"""
    try:
        result = manager.handle('', sys.argv[1:])
    except SystemExit as exception:
        result = exception.code
    sys.exit(result or 0)

if __name__ == '__main__':
    main()
