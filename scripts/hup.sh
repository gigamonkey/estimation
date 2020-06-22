#!/bin/bash

if [[ -e gunicorn.pid ]]; then
    kill -HUP $(cat gunicorn.pid)
else
    echo "No pidfile: gunicorn.pid"
fi
