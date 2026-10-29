project('158 protoc input outside root')

codegen = import('unstable-codegen')

protobuf = dependency('protobuf', required: false)
protoc = codegen.protoc(dependency: protobuf, required: false)
if not protobuf.found() or not protoc.found()
  error('MESON_SKIP_TEST protoc or protobuf not found.')
endif

x_proto = files('x.proto')
subdir('sub')
