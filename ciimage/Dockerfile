FROM ubuntu:bionic

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y update && apt-get -y upgrade \
&& apt-get -y install wget unzip \
&& apt-get -y build-dep meson \
&& apt-get -y install qt5-default qtbase5-private-dev clang \
&& apt-get -y install pkg-config-arm-linux-gnueabihf \
&& apt-get -y install doxygen \
&& apt-get -y install python3-pip libxml2-dev libxslt1-dev cmake libyaml-dev \
&& apt-get -y install qt4-linguist-tools \
&& apt-get -y install python-dev \
&& apt-get -y install libomp-dev openssh-client \
&& python3 -m pip install hotdoc codecov

# OpenSSH client is needed to run openmpi binaries.

ENV LANG='C.UTF-8'
