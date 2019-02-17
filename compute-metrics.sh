#!/usr/bin/env bash
echo "Computing metrics per $1 on file user_project_date_totalcommits.csv"
python szzComputeMetrics.py user_project_date_totalcommits.csv "$1"

echo "Computing metrics per $1 on file user_language_date_totalcommits.csv"
python szzComputeMetrics.py user_language_date_totalcommits.csv "$1"
