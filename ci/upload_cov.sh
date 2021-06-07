#!/bin/bash

echo "Combining coverage reports..."
coverage combine

echo "Generating XML report..."
coverage xml

echo "Printing report"
coverage report

echo "Uploading to codecov..."
codecov -f .coverage/coverage.xml -n "$1"
