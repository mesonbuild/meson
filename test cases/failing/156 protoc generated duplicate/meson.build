project('156 protoc generated duplicate')

codegen = import('unstable-codegen')

protobuf = dependency('protobuf', required: false)
protoc = codegen.protoc(dependency: protobuf, required: false)
if not protobuf.found() or not protoc.found()
  error('MESON_SKIP_TEST protoc or protobuf not found.')
endif

gen_proto = configure_file(input: 'x.proto.in', output: 'x.proto', copy: true)

gen = protoc.generate('x.proto', gen_proto, language: 'cpp')
