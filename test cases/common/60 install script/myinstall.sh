#!/bin/sh

set -eu

echo Starting custom installation step

mkdir -p "${DESTDIR}${MESON_INSTALL_PREFIX}/diiba/daaba"
touch "${DESTDIR}${MESON_INSTALL_PREFIX}/diiba/daaba/file.dat"

echo Finished custom install step
