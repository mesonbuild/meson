FROM ubuntu:zesty

RUN apt-get -y update && apt-get -y upgrade \
&& apt-get -y install git wget unzip \
&& apt-get -y build-dep meson \
&& apt-get -y install qt5-default itstool clang libgtk-3-dev \
&& apt-get -y install pkg-config-arm-linux-gnueabihf g++-6-arm-linux-gnueabihf \
&& apt-get -y install valgrind doxygen \
&& apt-get -y install llvm libsdl2-dev \
&& apt-get -y install python3-pip libxml2-dev libxslt1-dev cmake libyaml-dev \
&& apt-get -y install openmpi-bin libopenmpi-dev \
&& apt-get -y install libvulkan-dev \
&& python3 -m pip install hotdoc codecov
