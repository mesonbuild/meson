# Continuous Integration

Here you will find snippets to use Meson with various CI such as
Travis and AppVeyor.

Please [file an issue](https://github.com/mesonbuild/meson/issues/new)
if these instructions don't work for you.

## Travis-CI with Docker

Travis with Docker gives access to newer non-LTS Ubuntu versions with
pre-installed libraries of your choice.

This `yml` file is derived from the
[configuration used by Meson](https://github.com/mesonbuild/meson/blob/master/.travis.yml)
for running its own tests.

```yaml
os:
  - linux
  - osx

language:
  - cpp

services:
  - docker

before_install:
  - if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then brew update; fi
  - if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then brew install python3 ninja; fi
  - if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then pip3 install meson; fi
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then docker pull YOUR/REPO:eoan; fi

script:
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then echo FROM YOUR/REPO:eoan > Dockerfile; fi
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then echo ADD . /root >> Dockerfile; fi
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then docker build -t withgit .; fi
  - if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then docker run withgit /bin/sh -c "cd /root && TRAVIS=true CC=$CC CXX=$CXX meson setup builddir && meson test -C builddir"; fi
  - if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then SDKROOT=$(xcodebuild -version -sdk macosx Path) meson setup builddir && meson test -C builddir; fi
```

## CircleCI for Linux host (with custom Docker images)

[CircleCi](https://circleci.com/) can work for spinning all of the
Linux images you wish. Here's a sample `yml` file for use with that.

```yaml
version: 2.1

executors:
  # Your dependencies would go in the docker images that represent
  # the Linux distributions you are supporting
  meson_ubuntu_builder:
    docker:
      - image: your_dockerhub_username/ubuntu-sys

  meson_debian_builder:
    docker:
      - image: your_dockerhub_username/debian-sys

  meson_fedora_builder:
    docker:
      - image: your_dockerhub_username/fedora-sys

jobs:
  meson_ubuntu_build:
    executor: meson_ubuntu_builder
    steps:
      - checkout
      - run:
          name: Configure Project
          command: meson setup builddir --backend ninja
      - run:
          name: Compile Project
          command: meson compile -C builddir
      - run:
          name: Run Tests
          command: meson test -C builddir

  meson_debian_build:
    executor: meson_debian_builder
    steps:
      - checkout
      - run:
          name: Configure Project
          command: meson setup builddir --backend ninja
      - run:
          name: Compile Project
          command: meson compile -C builddir
      - run:
          name: Run Tests
          command: meson test -C builddir

  meson_fedora_build:
    executor: meson_fedora_builder
    steps:
      - checkout
      - run:
          name: Configure Project
          command: meson setup builddir --backend ninja
      - run:
          name: Compile Project
          command: meson compile -C builddir
      - run:
          name: Run Tests
          command: meson test -C builddir

workflows:
  version: 2
  linux_workflow:
    jobs:
      - meson_ubuntu_build
      - meson_debian_build
      - meson_fedora_build

```

## CircleCI for Linux host (without custom Docker images)

This CircleCI configuration defines two jobs, `build-linux` and `build-macos`,
within a workflow named `build`. The `build-linux` job utilizes a Docker image
with Python 3.12.3, while `build-macos` runs on macOS with Xcode 15.3.0. Each
job involves checking out the code, installing Meson and Ninja, configuring the
project, compiling it, and running tests using Meson.

```yaml
version: 2.1

jobs:
  build-linux:
    docker:
      - image: cimg/python:3.12.3
    steps:
      - checkout
      - run:
          name: Install Meson and Ninja
          command: |
            python -m pip install --user meson ninja
      - run:
          name: Configure Project
          command: |
            meson setup builddir
      - run:
          name: Compile Project
          command: |
            meson compile -C builddir
      - run:
          name: Run Tests
          command: |
            meson test -C builddir

  build-macos:
    macos:
      xcode: 15.3.0
    steps:
      - checkout
      - run:
          name: Install Meson and Ninja
          command: |
            python -m pip install meson ninja
      - run:
          name: Configure Project
          command: |
            meson setup builddir
      - run:
          name: Compile Project
          command: |
            meson compile -C builddir
      - run:
          name: Run Tests
          command: |
            meson test -C builddir

workflows:
  version: 2.1
  build:
    jobs:
      - build-linux
      - build-macos
```

## AppVeyor for Windows

For CI on Windows, [AppVeyor](https://www.appveyor.com/) has a wide
selection of [default
configurations](https://www.appveyor.com/docs/windows-images-software/).
AppVeyor also has
[MacOS](https://www.appveyor.com/docs/macos-images-software/) and
[Linux](https://www.appveyor.com/docs/linux-images-software/) CI
images. This is a sample `appveyor.yml` file for Windows with Visual
Studio 2017, 2019, and 2022.

```yaml
version: 1.0.{build}
image:
- Visual Studio 2022
- Visual Studio 2019
- Visual Studio 2017

install:
- cmd: python -m pip install meson ninja

build_script:
- cmd: >-
    meson setup builddir
    meson compile -C builddir

test_script:
- cmd: meson test -C builddir
```

### Qt

For Qt 5, add the following line near the `PYTHON_ROOT` assignment:

```yaml
 - cmd: if %arch%==x86 (set QT_ROOT=C:\Qt\5.11\%compiler%) else (set QT_ROOT=C:\Qt\5.11\%compiler%_64)
```

And afterwards add `%QT_ROOT%\bin` to the `PATH` variable.

You might have to adjust your build matrix as there are, for example,
no msvc2017 32-bit builds. Visit the [Build
Environment](https://www.appveyor.com/docs/build-environment/) page in
the AppVeyor docs for more details.

### Boost

The following statement is sufficient for Meson to find Boost:

```yaml
 - cmd: set BOOST_ROOT=C:\Libraries\boost_1_67_0
```

## Travis without Docker

Non-Docker Travis-CI builds can use Linux, MacOS or Windows.
Set the desired compiler(s) in the build **matrix**.
This example is for **Linux** (Ubuntu 18.04) and **C**.

```yaml
dist: bionic
group: travis_latest

os: linux
language: python

matrix:
  include:
    - env: CC=gcc
    - env: CC=clang

install:
  - pip install meson ninja

script:
  - meson setup builddir
  - meson compile -C builddir
  - meson test -C builddir
```

## GitHub Actions

GitHub Actions provides a versatile platform for continuous integration
(CI). This example workflow file, `ci_meson.yml`, is tailored for C-based
projects utilizing GCC on Linux, macOS, and Windows. Triggered by changes
to C code files, it automates building and testing processes using different
versions of Meson (1.0.0, 1.1.0, 1.2.0, 1.3.0, 1.4.0) across various operating
systems. Each job in the workflow handles checkout, dependency installation,
project configuration, test execution, and optional test log uploads upon
failure.

```yaml
name: CI Meson

on:
  push:
    paths:
      - "**.c"
      - "**.h"
  pull_request:
    paths:
      - "**.c"
      - "**.h"

jobs:
  build:
    name: Build and Test on ${{ matrix.os }} with Meson v${{ matrix.meson_version }}
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        meson_version: ["1.2.0", "1.3.0", "1.4.0"]
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - name: Install dependencies
        run: python -m pip install meson==${{ matrix.meson_version }} ninja
      - name: Configure Project
        run: meson setup builddir/
        env:
          CC: gcc
      - name: Run Tests
        run: meson test -C builddir/ -v
      - name: Upload Test Log
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: ${{ matrix.os }}_Meson_Testlog
          path: builddir/meson-logs/testlog.txt

```
