#!/usr/bin/zsh

# This script must be run from the source root.

set -e

GENDIR=distgendir

rm -rf dist
rm -rf $GENDIR
mkdir dist
mkdir $GENDIR
cp -r .git $GENDIR
cd $GENDIR
git reset --hard
python3 setup.py sdist bdist_wheel
cp dist/* ../dist
cd ..
rm -rf $GENDIR
