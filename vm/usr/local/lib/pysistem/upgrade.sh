#!/bin/bash
pushd "$HOME/env/pysistem" > /dev/null 2>&1
cd "$HOME/env/pysistem"
. "$HOME/env/pysistem/bin/activate"
echo "Upgrading PySistem..."
mkdir -p "temporary"
cd "temporary"
git clone "https://github.com/TsarN/pysistem"
if [ -e "../pysistem/conf.py" ]; then
	mv "../pysistem/conf.py" .
fi
if [ -e "../pysistem/storage" ]; then
	mv "../pysistem/storage" .
fi
rm -f "pysistem/pysistem/conf.py"
rm -rf "../pysistem"
mv "pysistem/pysistem" "../pysistem"
if [ -e "conf.py" ]; then
	mv "conf.py" "../pysistem/conf.py"
fi
if [ -e "storage" ]; then
	mv "storage" "../pysistem/storage"
fi
cd ..
pybabel compile -d "pysistem/translations"
popd > /dev/null 2>&1
