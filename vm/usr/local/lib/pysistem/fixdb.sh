#!/bin/bash
echo "Factory resetting database..." &&
"/usr/local/lib/pysistem/generateschema.sh" | mysql -u root -p &&
echo "Clearing storage" &&
rm -rf "$HOME/env/pysistem/pysistem/storage"
