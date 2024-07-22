#!/usr/bin/env bash
cd ./da/eth-specs
pip install -r requirements_preinstallation.txt
python setup.py sdist bdist_wheel
pip install dist/*.whl