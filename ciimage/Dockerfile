FROM ubuntu:artful

RUN apt-get -y update && apt-get -y upgrade \
&& apt-get -y install git wget unzip \
&& apt-get -y build-dep meson \
&& apt-get -y install qt5-default clang \
&& apt-get -y install pkg-config-arm-linux-gnueabihf g++-7-arm-linux-gnueabihf \
&& apt-get -y install doxygen \
&& apt-get -y install python3-pip libxml2-dev libxslt1-dev cmake libyaml-dev \
&& apt-get -y install libcups2-dev \
&& apt-get -y install gcovr lcov \
&& apt-get -y install fpga-icestorm arachne-pnr yosys \
&& apt-get -y install gtk-sharp2 gtk-sharp2-gapi libglib2.0-cil-dev \
&& apt-get -y install libwmf-dev \
&& apt-get -y install qt4-linguist-tools qttools5-dev-tools \
&& python3 -m pip install hotdoc codecov
