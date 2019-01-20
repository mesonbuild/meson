# Continuous Integration

Here you will find snippets to use Meson with various CI such as
Travis and AppVeyor.

Please [file an issue](https://github.com/mesonbuild/meson/issues/new)
if these instructions don't work for you.

## Travis for OS X and Linux (with Docker)

Travis for Linux provides ancient versions of Ubuntu which will likely
cause problems building your projects regardless of which build system
you're using. We recommend using Docker to get a more-recent version
of Ubuntu and installing Ninja, Python3, and Meson inside it.

This `yml` file is derived from the [configuration used by Meson for
running its own
tests](https://github.com/mesonbuild/meson/blob/master/.travis.yml).

```yaml
sudo: false

os:
  - linux
  - osx

language:
  - cpp

services:
  - docker

before_install:
  - if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then brew update; fi
  - if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then brew install ninja python3; fi
  - if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then pip3 install meson; fi
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then docker pull YOUR/REPO:yakkety; fi

script:
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then echo FROM YOUR/REPO:yakkety > Dockerfile; fi
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then echo ADD . /root >> Dockerfile; fi
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then docker build -t withgit .; fi
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then docker run withgit /bin/sh -c "cd /root && TRAVIS=true CC=$CC CXX=$CXX meson builddir && ninja -C builddir test"; fi
  - if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then SDKROOT=$(xcodebuild -version -sdk macosx Path) meson builddir && ninja -C builddir test; fi
```

## AppVeyor for Windows

For CI on Windows, [AppVeyor](https://www.appveyor.com/) is probably
your best bet. Here's a sample `yml` file for use with that.

```yaml
os: Visual Studio 2017

environment:
  matrix:
    - arch: x86
      compiler: msvc2015
    - arch: x64
      compiler: msvc2015
    - arch: x86
      compiler: msvc2017
    - arch: x64
      compiler: msvc2017

platform:
  - x64

install:
  # Download ninja
  - cmd: mkdir C:\ninja-build
  - ps: (new-object net.webclient).DownloadFile('https://github.com/mesonbuild/cidata/raw/master/ninja.exe', 'C:\ninja-build\ninja.exe')
  # Set paths to dependencies (based on architecture)
  - cmd: if %arch%==x86 (set PYTHON_ROOT=C:\python37) else (set PYTHON_ROOT=C:\python37-x64)
  # Print out dependency paths
  - cmd: echo Using Python at %PYTHON_ROOT%
  # Add neccessary paths to PATH variable
  - cmd: set PATH=%cd%;C:\ninja-build;%PYTHON_ROOT%;%PYTHON_ROOT%\Scripts;%PATH%
  # Install meson
  - cmd: pip install meson
  # Set up the build environment
  - cmd: if %compiler%==msvc2015 ( call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" %arch% )
  - cmd: if %compiler%==msvc2017 ( call "C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Auxiliary\Build\vcvarsall.bat" %arch% )

build_script:
  - cmd: echo Building on %arch% with %compiler%
  - cmd: meson --backend=ninja builddir
  - cmd: ninja -C builddir

test_script:
  - cmd: ninja -C builddir test
```

### Qt

For Qt 5, add the following line near the `PYTHON_ROOT` assignment:
```yaml
 - cmd: if %arch%==x86 (set QT_ROOT=C:\Qt\5.11\%compiler%) else (set QT_ROOT=C:\Qt\5.11\%compiler%_64)
```
And afterwards add `%QT_ROOT%\bin` to the `PATH` variable.

You might have to adjust your build matrix as there are, for example, no msvc2017 32-bit builds. Visit the [Build Environment](https://www.appveyor.com/docs/build-environment/) page in the AppVeyor docs for more details.

### Boost

The following statement is sufficient for meson to find Boost:
```yaml
 - cmd: set BOOST_ROOT=C:\Libraries\boost_1_67_0
```

## Travis without Docker

You can cheat your way around docker by using **python** as language and setting your compiler in the build **matrix**. This example just uses **linux** and **c** but can be easily adapted to **c++** and **osx**.

```yaml
sudo: false

os: linux
dist: trusty

language: python

python: 3.6

matrix:
  include:
    - env: CC=gcc
    - env: CC=clang

install:
  - export NINJA_LATEST=$(curl -s https://api.github.com/repos/ninja-build/ninja/releases/latest | grep browser_download_url | cut -d '"' -f 4 | grep ninja-linux.zip)
  - wget "$NINJA_LATEST"
  - unzip -q ninja-linux.zip -d build
  - export PATH="$PWD/build:$PATH"
  - pip install meson

script:
  - meson builddir
  - ninja -C builddir
  - ninja -C builddir test
```

This setup uses the **beta** group. It is not recommended but included here for completeness:

```yaml
sudo: false
language: cpp
group: beta

matrix:
  include:
    - os: linux
      dist: trusty
    - os: osx

install:
  - export PATH="$(pwd)/build:${PATH}"
  - if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then brew update && brew install python3 ninja; fi
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then wget https://github.com/ninja-build/ninja/releases/download/v1.7.2/ninja-linux.zip && unzip -q ninja-linux.zip -d build; fi
  - pip3 install meson

script:
  - meson builddir
  - ninja -C builddir
  - ninja -C builddir test
```
