#!/bin/bash

nohup gunicorn -p gunicorn.pid -b 127.0.0.1:8080 web:app &
