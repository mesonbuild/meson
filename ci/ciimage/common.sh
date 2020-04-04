#!/bin/bash

###
### Common functions for CI builder files.
### All functions can be accessed in install.sh via:
###
### $ source /ci/common.sh
###

set -e

dub_fetch() {
  set +e
  for (( i=1; i<=24; ++i )); do
    dub fetch "$@"
    (( $? == 0 )) && break

    echo "Dub Fetch failed. Retrying in $((i*5))s"
    sleep $((i*5))
  done
  set -e
}
