#!/bin/bash

set -e

msg() { echo -e "\x1b[1;32mINFO:  \x1b[37m$*\x1b[0m"; }

if [[ "$TRAVIS_OS_NAME" == "linux" ]]; then
  # TODO enable coverage
  #curl -s https://codecov.io/bash > upload.sh
  #chmod +x upload.sh

  # We need to copy the current checkout inside the Docker container,
  # because it has the MR id to be tested checked out.

  msg "Generating runner:"
  cat <<EOF | tee run.sh
#!/bin/bash

set -e

export CC=$CC
export CXX=$CXX
export OBJC=$CC
export OBJCXX=$CXX
export PATH=/root/tools:$PATH
if test "$MESON_RSP_THRESHOLD" != ""
then
  export MESON_RSP_THRESHOLD=$MESON_RSP_THRESHOLD
fi

source /ci/env_vars.sh
cd /root

./run_tests.py $RUN_TESTS_ARGS -- $MESON_ARGS
#./upload.sh

EOF

  chmod +x run.sh

  msg "Generating Dockerfile:"
  cat <<EOF | tee Dockerfile
FROM mesonbuild/eoan
ADD . /root

EOF

  msg "Building the docker image..."
  docker build -t test_img .

  msg "Start running tests"
  #ci_env=`bash <(curl -s https://codecov.io/env)`
  docker run --security-opt seccomp:unconfined test_img /root/run.sh

elif [[ "$TRAVIS_OS_NAME" == "osx"   ]]; then
  # Ensure that llvm is added after $PATH, otherwise the clang from that llvm install will be used instead of the native apple clang.
  export SDKROOT=$(xcodebuild -version -sdk macosx Path)
  export CPPFLAGS=-I/usr/local/include LDFLAGS=-L/usr/local/lib
  export OBJC=$CC
  export OBJCXX=$CXX
  export PATH=$HOME/tools:/usr/local/opt/qt/bin:$PATH:$(brew --prefix llvm)/bin
  if test "$MESON_RSP_THRESHOLD" != ""
  then
    export MESON_RSP_THRESHOLD=$MESON_RSP_THRESHOLD
  fi
  ./run_tests.py $RUN_TESTS_ARGS --backend=ninja -- $MESON_ARGS
fi
