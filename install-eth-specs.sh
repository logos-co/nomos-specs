#!/usr/bin/env bash

pip3 -r ./eth-specs/requirements_preinstallation.txt
python3 ./eth-specs/setup.py sdist bdist_wheel
pip3 install ./eth-specs/dist/*.whl