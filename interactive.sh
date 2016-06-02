#!/bin/bash
modules=(checkers compilers contests problems submissions test_pairs users)
echo "from pysistem import db, app" > /tmp/pysistem_startup
for mod in ${modules[@]}; do
    echo "from pysistem.${mod}.model import *" >> /tmp/pysistem_startup
done
PYTHONSTARTUP="/tmp/pysistem_startup" python3
rm -f "/tmp/pysistem_startup"
