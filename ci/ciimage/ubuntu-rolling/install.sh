#!/bin/bash

set -e

source /ci/common.sh

export DEBIAN_FRONTEND=noninteractive
export LANG='C.UTF-8'
export DC=gdc

pkgs=(
  python3-pip libxml2-dev libxslt1-dev libyaml-dev libjson-glib-dev
  wget unzip
  qt5-qmake qtbase5-dev qtchooser qtbase5-dev-tools clang
  pkg-config-arm-linux-gnueabihf
  libomp-dev
  llvm lcov
  dub ldc
  mingw-w64 mingw-w64-tools nim
  libclang-dev
  libgcrypt20-dev
  libgpgme-dev
  libhdf5-dev
  libboost-python-dev libboost-regex-dev
  libblocksruntime-dev
  libperl-dev
  liblapack-dev libscalapack-mpi-dev
  bindgen
)

sed -i '/^#\sdeb-src /s/^#//' "/etc/apt/sources.list"
apt-get -y update
apt-get -y upgrade
apt-get -y install eatmydata

# Base stuff
eatmydata apt-get -y build-dep meson

# packages
eatmydata apt-get -y install "${pkgs[@]}"
eatmydata apt-get -y install --no-install-recommends wine-stable  # Wine is special

install_python_packages hotdoc

# dub stuff
dub_fetch urld
dub build urld --compiler=gdc
dub_fetch dubtestproject
dub build dubtestproject:test1 --compiler=ldc2
dub build dubtestproject:test2 --compiler=ldc2

# cleanup
apt-get -y clean
apt-get -y autoclean
