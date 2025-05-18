#!/bin/bash

set -e

source /ci/common.sh

export DEBIAN_FRONTEND=noninteractive
export LANG='C.UTF-8'

apt-get -y update
apt-get -y upgrade
apt-get -y install wget

# Cuda repo + keyring.
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
apt-get -y install ./cuda-keyring_1.1-1_all.deb

# Cuda cross repo.
echo "deb [signed-by=/usr/share/keyrings/cuda-archive-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/cross-linux-aarch64/ /" \
  > /etc/apt/sources.list.d/cuda-ubuntu2204-cross-linux-aarch64.list
apt-get -y update

pkgs=(
  clang cmake crossbuild-essential-arm64 cuda-cross-aarch64
  cuda-nvcc-12-9 git libglib2.0-dev ninja-build pkg-config python3-pip
)

apt-get -y install "${pkgs[@]}"

install_minimal_python_packages

# Tests need nvcc in PATH in order to run cuda tests.
echo "export PATH=\$PATH:/usr/local/cuda/bin" >> /ci/env_vars.sh

# cleanup
apt-get -y clean
apt-get -y autoclean
rm cuda-keyring_1.1-1_all.deb
