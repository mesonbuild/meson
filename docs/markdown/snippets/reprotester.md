## Simple tool to test build reproducibility

Meson now ships with a command for testing whether your project can be
[built reprodicibly](https://reproducible-builds.org/). It can be used
by running a command like the following in the source root of your
project:

    meson reprotest --intermediaries -- --buildtype=debugoptimized

All command line options after the `--` are passed to the build
invocations directly.

This tool is not meant to be exhaustive, but instead easy and
convenient to run. It will detect some but definitely not all
reproducibility issues.
