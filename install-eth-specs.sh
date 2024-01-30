#!/usr/bin/env bash

pip install -r ./eth-specs/requirements_preinstallation.txt
python ./eth-specs/setup.py sdist bdist_wheel
pip install ./eth-specs/dist/*.whl