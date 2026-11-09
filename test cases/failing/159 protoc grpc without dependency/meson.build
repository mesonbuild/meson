project('159 protoc grpc without dependency')

codegen = import('unstable-codegen')

protobuf = dependency('protobuf', required: false)
protoc = codegen.protoc(dependency: protobuf, required: false)
if not protobuf.found() or not protoc.found()
  error('MESON_SKIP_TEST protoc or protobuf not found.')
endif

gen = protoc.generate('x.proto', grpc: true)
