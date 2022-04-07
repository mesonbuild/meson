#!/bin/bash

set -e

source /ci/common.sh

export DEBIAN_FRONTEND=noninteractive
export LANG='C.UTF-8'
export DC=gdc

pkgs=(
  python3-pip libxml2-dev libxslt1-dev libyaml-dev libjson-glib-dev
  python3.7 python3.7-dev
  wget unzip cmake doxygen
  clang
  pkg-config-arm-linux-gnueabihf
  qt4-linguist-tools qt5-default qtbase5-private-dev
  python-dev
  libomp-dev
  llvm lcov
  ldc
  libclang-dev
  libgcrypt20-dev
  libgpgme-dev
  libhdf5-dev openssh-server
  libboost-python-dev libboost-regex-dev
  libblocksruntime-dev
  libperl-dev libscalapack-mpi-dev libncurses-dev
  itstool
  openjdk-11-jre
)

boost_pkgs=(atomic chrono date-time filesystem log regex serialization system test thread)

sed -i '/^#\sdeb-src /s/^#//' "/etc/apt/sources.list"
apt-get -y update
apt-get -y upgrade
apt-get -y install eatmydata

# Base stuff
eatmydata apt-get -y build-dep meson

# Add boost packages
for i in "${boost_pkgs[@]}"; do
  for j in "1.62.0" "1.65.1"; do
    pkgs+=("libboost-${i}${j}")
  done
done

# packages
eatmydata apt-get -y install "${pkgs[@]}"

# Actually select the right python version
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 1 \
    --slave /usr/lib/x86_64-linux-gnu/pkgconfig/python3.pc python3.pc /usr/lib/x86_64-linux-gnu/pkgconfig/python-3.6.pc
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.7 2 \
    --slave /usr/lib/x86_64-linux-gnu/pkgconfig/python3.pc python3.pc /usr/lib/x86_64-linux-gnu/pkgconfig/python-3.7.pc

python3 -m pip install -U "${base_python_pkgs[@]}" "${python_pkgs[@]}"

pushd /opt
# Download and install PyPy3.8, and link it to /usr/bin/pypy3
# At some point it would be more robust to download and parse
# https://downloads.python.org/pypy/versions.json
wget https://downloads.python.org/pypy/pypy3.8-v7.3.9-linux64.tar.bz2
pypy_sha256="08be25ec82fc5d23b78563eda144923517daba481a90af0ace7a047c9c9a3c34"
if [ $pypy_sha256 != $(sha256sum pypy3.8-v7.3.9-linux64.tar.bz2 | cut -f1 -d" ") ]; then
  echo bad sha256 for PyPy
  exit -1
fi
tar -xf pypy3.8-v7.3.9-linux64.tar.bz2
pypy3.8-v7.3.9-linux64/bin/pypy3 -m ensurepip
popd
ln -s /opt/pypy3.8-v7.3.9-linux64/bin/pypy3 /usr/bin/pypy3


# Install the ninja 0.10
wget https://github.com/ninja-build/ninja/releases/download/v1.10.0/ninja-linux.zip
unzip ninja-linux.zip -d /ci

# cleanup
apt-get -y remove ninja-build
apt-get -y clean
apt-get -y autoclean
rm ninja-linux.zip
