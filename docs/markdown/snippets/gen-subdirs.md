## Generator outputs can preserve directory structure

Normally when generating files with a generator, Meson flattens the
input files so they all go in the same directory. Some code
generators, such as Protocol Buffers, require that the generated files
have the same directory layout as the input files used to generate
them. This can now be achieved like this:

```meson
g = generator(...) # Compiles protobuf sources
generated = gen.process('com/mesonbuild/one.proto',
  'com/mesonbuild/two.proto',
  preserve_path_from : meson.current_source_dir())

This would cause the following files to be generated inside the target
private directory:

    com/mesonbuild/one.pb.h
    com/mesonbuild/one.pb.cc
    com/mesonbuild/two.pb.h
    com/mesonbuild/two.pb.cc
