project('157 protoc same proto twice')

codegen = import('unstable-codegen')

protobuf = dependency('protobuf', required: false)
protoc = codegen.protoc(dependency: protobuf, required: false)
if not protobuf.found() or not protoc.found()
  error('MESON_SKIP_TEST protoc or protobuf not found.')
endif

# Both calls produce the same outputs in the same directory.
gen1 = protoc.generate('x.proto', language: 'cpp')
gen2 = protoc.generate('x.proto', language: 'cpp')
