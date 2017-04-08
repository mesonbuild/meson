#!/bin/sh

echo ninja $(ninja --version)
python3 --version -V

python3 run_tests.py --backend=${backend}
