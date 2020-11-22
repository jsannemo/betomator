#!/bin/bash

if [ "$FLASK_ENV" == "development" ]; then
        flask run
else
        gunicorn app:app -w 1
fi
