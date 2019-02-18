#!/usr/bin/env bash
export PYTHONPATH=.:$PYTHONPATH
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
if [ -z "$4" ]; then
    python szz/SzzAlgorithm.py --repo=$1 --issues=$2 --output=$3
elif [ -z "$5" ]; then
    mpiexec -n $1 python szz/SzzAlgorithm.py --repo=$2 --issues=$3 --output=$4
else
    export PATH=$PATH:$1
    mpiexec -n $2 python szz/SzzAlgorithm.py --repo=$3 --issues=$4 --output=$5
fi