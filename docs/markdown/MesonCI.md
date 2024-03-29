# Meson CI setup

This document is aimed for Meson contributors and documents the CI
setup used for testing Meson itself. The Meson project uses multiple
CI platforms for covering a wide range of target systems.

## GitHub actions

The configuration files for GitHub actions are located in
`.github/workflows`. Here, all [images](#docker-images) are tested
with the full `run_tests.py` run. Additionally, some other, smaller,
tests are run.

## Docker images

The Linux docker images are automatically built and uploaded by GitHub
actions. An image rebuild is triggered when any of the image definition
files are changed (in `ci/ciimage`) in the master branch.
Additionally, the images are also updated weekly.

Each docker image has one corresponding directory in `ci/ciimage` with
an `image.json` and an `install.sh`.

### Image generation

There are no manual Dockerfiles. Instead the Dockerfile is
automatically generated by the `build.py` script. This is done to
ensure that all images have the same layout and can all be built and
tested automatically.

The Dockerfile is generated from the `image.json` file and basically
only adds a few common files and runs the `install.sh` script which
should contain all distribution specific setup steps. The `common.sh`
can be sourced via `source /ci/common.sh` to access some shared
functionality.

To generate the image run `build.py -t build <image>`. A generated
image can be tested with `build.py -t test <image>`.

### Common image setup

Each docker image has a `/ci` directory with an `env_vars.sh` script.
This script has to be sourced before running the Meson test suite.
