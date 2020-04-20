#!/bin/bash

set -e

msg() { echo -e "\x1b[1;32mINFO:  \x1b[37m$*\x1b[0m"; }

if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
  msg "Running OSX setup"
  brew update
  brew install qt ldc llvm ninja
  if [[ "$MESON_ARGS" =~ .*unity=on.* ]]; then
    which pkg-config || brew install pkg-config
  fi
  python3 -m pip install jsonschema
elif [[ "$TRAVIS_OS_NAME" == "linux" ]]; then
  msg "Running Linux setup"
  docker pull mesonbuild/eoan
fi

msg "Setup finished"
