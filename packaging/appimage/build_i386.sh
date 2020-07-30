#!/bin/sh

cd "$(dirname "$0")"
SCRIPT="$(basename "$0")"

if [ ! -f /.dockerenv ]; then
    IT_ARG='-it'
    [ "$NONINTERACTIVE" -eq 1 ] && IT_ARG=''
    docker run --rm $IT_ARG --platform linux/i386 -v "$(realpath "$PWD/../..")":/meson i386/alpine sh -c "/meson/packaging/appimage/$SCRIPT $(id -u) $(id -g)"
    $PWD/../../appimage/package.sh
    exit $?
fi

apk update
apk upgrade
apk add python3 patchelf gcc g++ make linux-headers libffi-dev zlib-dev xz-dev sqlite-dev openssl-dev openssl-libs-static argp-standalone ninja udev eudev-dev bash sudo git

adduser -HD -u $1 -g $2 meson

sudo -u meson ./build.py -d -o meson-i386.runtime
