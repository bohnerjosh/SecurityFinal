#!/bin/bash

FLASK_APP=bnp.server.__main__ FLASK_ENV=development SECRET_KEY=APPLES python -m flask run --host=0.0.0.0
