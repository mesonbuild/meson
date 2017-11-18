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
os: Visual Studio 2015

environment:
  matrix:
    - arch: x86
      compiler: msvc2010
    - arch: x86
      compiler: msvc2015
    - arch: x64
      compiler: msvc2015

platform:
  - x64

install:
  # Use the x86 python only when building for x86 for the cpython tests.
  # For all other archs (including, say, arm), use the x64 python.
  - ps: (new-object net.webclient).DownloadFile('https://www.dropbox.com/s/cyghxjrvgplu7sy/ninja.exe?dl=1', 'C:\projects\meson\ninja.exe')
  - cmd: if %arch%==x86 (set MESON_PYTHON_PATH=C:\python34) else (set MESON_PYTHON_PATH=C:\python34-x64)
  - cmd: echo Using Python at %MESON_PYTHON_PATH%
  - cmd: "%MESON_PYTHON_PATH%\\pip install meson"
  - cmd: if %compiler%==msvc2010 ( call "C:\Program Files (x86)\Microsoft Visual Studio 10.0\VC\vcvarsall.bat" %arch% )
  - cmd: if %compiler%==msvc2015 ( call "C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\vcvarsall.bat" %arch% )

build_script:
  - cmd: echo Building on %arch% with %compiler%
  - cmd: PATH=%cd%;%MESON_PYTHON_PATH%;%PATH%; && python meson.py --backend=ninja builddir
  - cmd: PATH=%cd%;%MESON_PYTHON_PATH%;%PATH%; && ninja -C builddir

test_script:
  - cmd: PATH=%cd%;%MESON_PYTHON_PATH%;%PATH%; && ninja -C builddir test
```

## Travis without Docker

This setup is not recommended but included here for completeness

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
  - export PATH="`pwd`/build:${PATH}"
  - if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then brew update && brew install python3 ninja; fi
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then wget https://github.com/ninja-build/ninja/releases/download/v1.7.2/ninja-linux.zip && unzip -q ninja-linux.zip -d build; fi
  - pip3 install meson

script:
  - meson builddir
  - ninja -C builddir
  - ninja -C builddir test
```
