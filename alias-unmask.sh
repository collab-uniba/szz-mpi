#!/usr/bin/env bash
export PYTHONPATH=.:$PYTHONPATH
echo "Unmasking aliases"
python alias/unmask_aliases.py $1 $2
