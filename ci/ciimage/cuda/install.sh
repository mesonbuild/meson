#!/bin/bash

set -e

pkgs=(
  python python-setuptools python-wheel python-pytest-xdist python-jsonschema
  ninja gcc gcc-objc git cmake gtest
  cuda zlib pkgconf
)

PACMAN_OPTS='--needed --noprogressbar --noconfirm'

pacman -Syu $PACMAN_OPTS "${pkgs[@]}"

# Manually remove cache to avoid GitHub space restrictions
rm -rf /var/cache/pacman

echo "source /etc/profile.d/cuda.sh" >> /ci/env_vars.sh
