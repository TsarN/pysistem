#!/bin/bash
modules=(checkers compilers contests problems submissions test_pairs users groups)
echo "from pysistem import db, app" > /tmp/pysistem_startup
for mod in ${modules[@]}; do
    echo "from pysistem.${mod}.model import *" >> /tmp/pysistem_startup
done
interpreter=python3
if which ipython3 > /dev/null 2>&1; then
    interpreter=ipython3
fi
PYTHONSTARTUP="/tmp/pysistem_startup" $interpreter
rm -f "/tmp/pysistem_startup"
