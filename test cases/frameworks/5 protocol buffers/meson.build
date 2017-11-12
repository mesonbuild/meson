project('protocol buffer test', 'cpp')

protobuf_dep = dependency('protobuf')
protoc = find_program('protoc')

if not protoc.found() or not protobuf_dep.found()
  error('MESON_SKIP_TEST: protoc tool and/or protobuf pkg-config dependency not found')
endif

# Builds a proto subtree from top_level meson.build.
# Currently build proto subtree from outside requires a little hack in order to get proto headers
# currectly on include paths. Building with subdir at the top level of proto subtree is a cleaner
# solution.
protos_basename = [
  'messages/dummy_messages',
  'dummy_service',
]
protos_src = []
protos_hdr = []
foreach p : protos_basename
  cc_target = custom_target(
    p.underscorify(),
    input: 'proto/' + p + '.proto',
    output: [p + '.pb.cc', p + '.pb.h'],
    command: [protoc, '-I', '@CURRENT_SOURCE_DIR@/proto', '--cpp_out', '@OUTDIR@', '@INPUT@']
  )
  protos_src += cc_target[0]
  protos_hdr += cc_target[1]
endforeach

# Builds another proto subtree in a subdir
subdir('proto_subdir')

# Builds proto trees with generators. This acturally looks cleaner than the custom_target
# approach, but with some limits: it requires that the current source dir to be treated as 
# proto root, instead of the top level of the proto tree. This may require changes of existing
# code.
proto_gen = generator(protoc, 
  arguments: ['-I', '@CURRENT_SOURCE_DIR@', '--cpp_out', '@BUILD_DIR@', '@INPUT@'],
  output: ['@ROOTNAME@.pb.cc', '@ROOTNAME@.pb.h'],
)
protos_name = [
  'proto_generator/messages/dummy_messages3.proto',
  'proto_generator/dummy_service3.proto',
]
protos_gen_src = proto_gen.process(protos_name)

dummy_bin = executable(
  'prog',
  ['src/prog.cpp', protos_src, protos_hdr, protos_subdir_src, protos_subdir_hdr, protos_gen_src],
  dependencies: protobuf_dep,
)
