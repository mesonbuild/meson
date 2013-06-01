project('protocol buffer test', 'cxx')

protoc = find_program('protoc', required : true)
dep = find_dep('protobuf', required : true)

gen = generator(protoc, \
  outputs  : ['@BASENAME@.pb.cc', '@BASENAME@.pb.h'],
  arguments : ['-I=@SOURCE_DIR@', '--cpp_out=@BUILD_DIR@', '@INPUT@'])

generated = gen.process('defs.proto')
e = executable('prog', 'main.cpp', generated,
 deps : dep)
add_test('prototest', e)
