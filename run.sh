#!/bin/bash

python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python filter.py
python appeal.py
python unique.py
python link.py
python analyze.py
python extract.py