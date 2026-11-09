project('protoc gRPC', 'cpp', meson_version: '>=1.13.0', default_options: ['cpp_std=c++17'])

protobuf = dependency('protobuf', required: false)
grpc = dependency('grpc++', required: false)
if not protobuf.found() or not grpc.found()
  error('MESON_SKIP_TEST protobuf or grpc++ dependency not found.')
endif

codegen = import('unstable-codegen')

protoc = codegen.protoc(dependency: protobuf, grpc_dependency: grpc, required: false)
if not protoc.found()
  error('MESON_SKIP_TEST protoc not found.')
endif

# gRPC is enabled by default because grpc_dependency was given.
# messages.proto has no service: grpc_cpp_plugin still writes its files.
gen = protoc.generate('greeter.proto', 'messages.proto', install: true)
assert(gen.sources().length() == 4)
assert(gen.headers().length() == 4)

# Explicit opt-out.
plain_gen = protoc.generate('plain/plain.proto', grpc: false, install: true)
assert(plain_gen.sources().length() == 1)
assert(plain_gen.headers().length() == 1)

e = executable('prog', 'main.cpp', dependencies: [gen.dependency(), plain_gen.dependency()])
test('grpctest', e)
