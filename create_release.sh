#!/bin/sh

version=`./meson.py --version`
git archive --prefix meson-${version}/ HEAD | gzip > meson_${version}.tar.gz

