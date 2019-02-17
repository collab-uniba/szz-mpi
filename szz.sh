#!/usr/bin/env bash
export PYTHONPATH=.:$PYTHONPATH
/usr/lib64/openmpi/bin/mpiexec -n $1 python szz/SzzAlgorithm.py --repo=$2 --issues=$3 --output=$4