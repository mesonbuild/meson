FROM ubuntu:eoan

ENV DEBIAN_FRONTEND noninteractive
ENV LANG='C.UTF-8'
ENV DC=gdc

RUN sed -i '/^#\sdeb-src /s/^#//' "/etc/apt/sources.list" \
&& apt-get -y update && apt-get -y upgrade \
&& apt-get -y install eatmydata \
&& eatmydata apt-get -y build-dep meson \
&& eatmydata apt-get -y install python3-pytest-xdist \
&& eatmydata apt-get -y install python3-pip libxml2-dev libxslt1-dev libyaml-dev libjson-glib-dev \
&& eatmydata python3 -m pip install hotdoc codecov \
&& eatmydata apt-get -y install wget unzip \
&& eatmydata apt-get -y install qt5-default clang \
&& eatmydata apt-get -y install pkg-config-arm-linux-gnueabihf \
&& eatmydata apt-get -y install qt4-linguist-tools \
&& eatmydata apt-get -y install python-dev \
&& eatmydata apt-get -y install libomp-dev \
&& eatmydata apt-get -y install dub ldc \
&& eatmydata apt-get -y install mingw-w64 mingw-w64-tools nim \
&& eatmydata apt-get -y install --no-install-recommends wine-stable \
&& eatmydata apt-get -y install libclang-dev \
&& eatmydata apt-get -y install libgcrypt20-dev \
&& eatmydata apt-get -y install libgpgme-dev \
&& eatmydata apt-get -y install libhdf5-dev \
&& eatmydata apt-get -y install libboost-python-dev \
&& eatmydata apt-get -y install libblocksruntime-dev \
&& eatmydata apt-get -y install libperl-dev \
&& eatmydata apt-get -y install liblapack-dev libscalapack-mpi-dev \
&& eatmydata dub fetch urld && dub build urld --compiler=gdc \
&& eatmydata dub fetch dubtestproject \
&& eatmydata dub build dubtestproject:test1 --compiler=ldc2 \
&& eatmydata dub build dubtestproject:test2 --compiler=ldc2
# OpenSSH client is needed to run openmpi binaries.

