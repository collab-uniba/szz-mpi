#!/usr/bin/env bash
export PYTHONPATH=.:$PYTHONPATH
if [ -z "$3" ]; then
    python cross_reference/extractor.py --input=$1
else
    python cross_reference/extractor.py --input=$1 --commit_pattern=$2 --issues_pattern=$3
fi