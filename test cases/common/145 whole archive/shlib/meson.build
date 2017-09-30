# Nothing in dylib.c uses func1, so the linker would throw it
# away and thus linking the exe would fail.
dylib = shared_library('shlib', '../dylib.c',
  link_whole : stlib)
