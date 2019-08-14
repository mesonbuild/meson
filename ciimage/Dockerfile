FROM ubuntu:cosmic

ENV DEBIAN_FRONTEND noninteractive
ENV LANG='C.UTF-8'
ENV DC=gdc

RUN sed -i '/^#\sdeb-src /s/^#//' "/etc/apt/sources.list" \
&& apt-get -y update && apt-get -y upgrade \
&& apt-get -y build-dep meson \
&& apt-get -y install python3-pytest-xdist \
&& apt-get -y install python3-pip libxml2-dev libxslt1-dev cmake libyaml-dev \
&& python3 -m pip install hotdoc codecov \
&& apt-get -y install wget unzip \
&& apt-get -y install qt5-default clang \
&& apt-get -y install pkg-config-arm-linux-gnueabihf \
&& apt-get -y install qt4-linguist-tools \
&& apt-get -y install python-dev \
&& apt-get -y install libomp-dev \
&& apt-get -y install dub ldc \
&& apt-get -y install mingw-w64 mingw-w64-tools nim \
&& apt-get -y install --no-install-recommends wine-stable \
&& apt-get -y install llvm-dev libclang-dev \
&& apt-get -y install libgcrypt11-dev \
&& apt-get -y install libgpgme-dev \
&& apt-get -y install libhdf5-dev \
&& apt-get -y install libboost-python-dev \
&& apt-get -y install libblocksruntime-dev \
&& dub fetch urld && dub build urld --compiler=gdc \
&& dub fetch dubtestproject \
&& dub build dubtestproject:test1 --compiler=ldc2 \
&& dub build dubtestproject:test2 --compiler=ldc2
# OpenSSH client is needed to run openmpi binaries.

