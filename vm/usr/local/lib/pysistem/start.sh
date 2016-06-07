#!/bin/bash

pid="$HOME/env/pysistem/pysistem.pid"

start_pysistem() {
    pushd "$HOME/env/pysistem" > /dev/null 2>&1
    if [ -e "$pid" ]; then
        echo "( warn ) PySistem is already running"
    else
        gunicorn pysistem:app &
        gunicorn_pid=$!
        echo "$gunicorn_pid" > "$pid"
    fi
    popd > /dev/null 2>&1
}

stop_pysistem() {
    pushd "$HOME/env/pysistem" > /dev/null 2>&1
    if [ -e "$pid" ]; then
        gunicorn_pid=$(cat $pid)
        kill "$gunicorn_pid"
        rm -f "$pid"
    else
        echo "( warn ) PySistem is not running"
    fi
    popd > /dev/null 2>&1
}

status_pysistem() {
    if [ -e "$pid" ]; then
        gunicorn_pid=$(cat $pid)
        echo "PySistem is running with pid $gunicorn_pid"
    else
        echo "PySistem is not running"
    fi
}

. "$HOME/env/pysistem/bin/activate"
if [ "$1" == "start" ]; then
    start_pysistem
    exit
fi
if [ "$1" == "stop" ]; then
    stop_pysistem
    exit
fi
if [ "$1" == "status" ]; then
    status_pysistem
    exit
fi
echo "Usage: pysistem <start|stop|status>"
