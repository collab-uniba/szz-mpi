#!/usr/bin/env bash
export PYTHONPATH=.:$PYTHONPATH
python githubutils/IssuesAndCommentsProcessor.py -s $1 -t $2 -o $3