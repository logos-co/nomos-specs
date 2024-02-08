#!/usr/bin/env bash

pip install maturin
git clone git@github.com:crate-crypto/py-arkworks-bls12381.git
cd py-arkworks-bls12381
maturin develop
cd ..
rm -rf py-arkworks-bls12381
