#!/bin/sh

version=`./meson.py -v`
git archive --prefix meson-${version}/ HEAD | gzip > meson_${version}.tar.gz

