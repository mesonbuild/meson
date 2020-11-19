#!/usr/bin/env bash

VERS=$(cmake --version | grep "cmake version")
VERS=${VERS//cmake version/}

echo -n $VERS
