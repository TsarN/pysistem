#!/bin/bash
. "$HOME/env/pysistem/bin/activate"
pushd "$HOME/env/pysistem" > /dev/null 2>&1
h=`echo 'from pysistem.users.model import User; print(User.signpasswd("admin", "gazorpazorpfield"))' | python`
cat "/usr/local/lib/pysistem/defaultschema.sql" | sed "s/__SIGNED_ADMIN_PASSWORD__/$h/g" 
popd > /dev/null 2>&1
