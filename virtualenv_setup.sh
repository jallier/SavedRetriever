#! /bin/bash
virtualenv -p python3 env
source env/bin/activate
pip install -r requirements.txt
deactivate
