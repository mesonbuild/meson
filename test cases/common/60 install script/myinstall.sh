#!/bin/sh

set -eu

echo Starting custom installation step

# These commands fail on Windows, but we don't really care.

mkdir -p "${DESTDIR}${MESON_INSTALL_PREFIX}/diiba/daaba"
touch "${DESTDIR}${MESON_INSTALL_PREFIX}/diiba/daaba/file.dat"

echo Finishing custom install step
