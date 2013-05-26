project('protocol buffer test', 'cxx')

protoc = find_program('protoc', required : true)
dep = find_dep('protobuf', required : true)

gen = generator(protoc, \
  output_name  : '@BASENAME@.pb.cc',
  arguments : ['-I=@SOURCE_DIR@', '--cpp_out=@BUILD_DIR@', '@INPUT@'])

generated = gen.process('defs.proto')
e = executable('prog', 'main.cpp', generated,
 include_dirs: include_directories('.'),
 dep : dep)
add_test('prototest', e)
