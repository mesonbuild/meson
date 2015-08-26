project('protocol buffer test', 'cpp')

protoc = find_program('protoc')
dep = dependency('protobuf')

gen = generator(protoc, \
  output    : ['@BASENAME@.pb.cc', '@BASENAME@.pb.h'],
  arguments : ['--proto_path=@SOURCE_DIR@', '--cpp_out=@BUILD_DIR@', '@INPUT@'])

generated = gen.process('defs.proto')
e = executable('prog', 'main.cpp', generated,
 dependencies : dep)
test('prototest', e)
