#!/usr/bin/env bash

pip install maturin
git clone --depth 1 --branch v0.3.4 git@github.com:crate-crypto/py-arkworks-bls12381.git
cd py-arkworks-bls12381
maturin develop
cd ..
rm -rf py-arkworks-bls12381
