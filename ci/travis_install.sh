#!/bin/bash

set -e

msg() { echo -e "\x1b[1;32mINFO:  \x1b[37m$*\x1b[0m"; }

msg "Running Linux setup"
docker pull mesonbuild/eoan
msg "Setup finished"
