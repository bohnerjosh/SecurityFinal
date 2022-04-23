#!/bin/bash

FLASK_APP=server.__main__ FLASK_ENV=development SECRET_KEY=APPLES python -m flask run --host=0.0.0.0 --port=8000
