#!/bin/bash

FLASK_APP=server.siteappserver FLASK_ENV=development SECRET_KEY=BANANNAS python -m flask run --host=0.0.0.0 --port=8324
