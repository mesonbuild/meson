#!/bin/sh
# Mimic the test harness in run_unittest.py for this test case
# FIXME: delete this file once tests are passing
set -ex
meson=$HOME/src/meson/meson.py

dir1="val1"
prefix1="/tmp/xyzzy/$dir1/prefix"
btmp1="/tmp/xyzzy/$dir1/btmp"
cd "$dir1"
   rm -rf "$btmp1" "$prefix1"
   $meson --prefix="$prefix1" . "$btmp1"
   ninja -v -C "$btmp1"
   ninja -C "$btmp1" install
cd ..

arch=x86_64-linux-gnu
if ! test -d /usr/lib/${arch}
then
  arch=.
fi
export PKG_CONFIG_PATH="${prefix1}/lib/$arch/pkgconfig:${prefix1}/lib/pkgconfig"
#export LIBRARY_PATH="${prefix1}/lib/${arch}:${prefix1}/lib"

dir2="val2"
prefix2="/tmp/xyzzy/$dir2/prefix"
btmp2="/tmp/xyzzy/$dir2/btmp"
cd "$dir2"
   rm -rf "$btmp2" "$prefix2"
   $meson --prefix="$prefix2" . "$btmp2"
   ninja -v -C "$btmp2"
   ninja -C "$btmp2" install
cd ..

export PKG_CONFIG_PATH="${prefix2}/lib/$arch/pkgconfig:${prefix2}/lib/pkgconfig"
#export LIBRARY_PATH="${prefix2}/lib/${arch}:${prefix2}/lib"
dir3="client"
prefix3="/tmp/xyzzy/$dir3/prefix"
btmp3="/tmp/xyzzy/$dir3/btmp"
cd "$dir3"
   rm -rf "$btmp3" "$prefix3"
   $meson --prefix="$prefix3" . "$btmp3"
   ninja -v -C "$btmp3"
   ninja -C "$btmp3" install
cd ..

case "$OS" in
Windows_NT) ;;
*)
  # Show any RPATH entries
  set +x
  for file in "$btmp1"/*.so "$btmp2"/*.so "$btmp3"/client "$prefix2"/lib/$arch/*.so "$prefix1"/lib/$arch/*.so "$prefix3"/bin/client
  do
    echo -n "${file}: "
    readelf -d "$file" | grep PATH || echo ""
  done
  set -x
  ;;
esac

# Run the app
export PATH="${prefix1}/bin:${prefix2}/bin:$PATH"
"$prefix3"/bin/client

rm -rf /tmp/xyzzy
