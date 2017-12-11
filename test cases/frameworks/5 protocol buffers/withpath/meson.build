# Testing protobuf files that are deeply hierarchical
# and must preserve their path segments in output files
# because protoc will always put it in there.

gen = generator(protoc, \
  output    : ['@BASENAME@.pb.cc', '@BASENAME@.pb.h'],
  preserve_path_from : meson.current_source_dir(),
  arguments : ['--proto_path=@CURRENT_SOURCE_DIR@', '--cpp_out=@BUILD_DIR@', '@INPUT@'])

generated = gen.process('com/mesonbuild/simple.proto',
  'com/mesonbuild/subsite/complex.proto')
e = executable('pathprog', 'pathprog.cpp', generated,
 dependencies : dep)
test('pathprog', e)
