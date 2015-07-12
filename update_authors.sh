#!/bin/sh
git log --no-merges --pretty=format:"%an" | sort | uniq > authors.txt
