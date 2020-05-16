## rpath removal now more careful

On Linux-like systems, meson adds rpath entries to allow running apps
in the build tree, and then removes those build-time-only
rpath entries when installing.  Rpath entries may also come
in via LDFLAGS and via .pc files.  Meson used to remove those
latter rpath entries by accident, but is now more careful.
