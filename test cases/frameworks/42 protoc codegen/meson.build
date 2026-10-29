project('ProtoBuf Code Generator', 'cpp', meson_version: '>=1.13.0', default_options: ['cpp_std=c++17'])

protobuf = dependency('protobuf', required: false)
if not protobuf.found()
  error('MESON_SKIP_TEST protobuf dependency not found.')
endif

codegen = import('unstable-codegen')

protoc = codegen.protoc(
  dependency: protobuf,
  version: '>=3.0',
  # Smoke test: protoc rejects unknown flags, so this checks that the
  # argument reaches protoc. gcc is the default format.
  args: '--error_format=gcc',
  required: false,
)

if not protoc.found()
  error('MESON_SKIP_TEST protoc not found.')
endif

message('protoc version: ' + protoc.version())

gen_proto = find_program('gen_proto.py')

# Coverage:
# - protos/: the main generate() root, with a nested proto, a configured
#   proto, custom_target() protos (whole and indexed, one in a child subdir),
#   and imports of the two directories below.
# - imported/: another generate() root, passed through `imports`, with a
#   source proto and a custom_target() proto in a child subdir.
# - import_dir/: another generate() root, passed through `import_dirs`, so the
#   C++ side must be added explicitly.
subdir('import_dir')
subdir('imported')
subdir('protos')

e = executable(
  'prog',
  'main.cpp',
  dependencies: [
    protos_gen.dependency(),
    # Already carried by protos_gen through `imports`: checks that the same
    # sources reached through two dependencies are only built once.
    imported_gen.dependency(),
    # Required: `import_dirs` only adds a protoc search path.
    import_dir_gen.dependency(),
  ],
)
test('prototest', e)

# Without dependency(): each .pb.cc finds its own .pb.h next to it, so a
# generate() call without imports can be compiled from sources() alone.
static_library('import_dir_lib', import_dir_gen.sources(), dependencies: protobuf)

# headers() as inputs of another target: toplevel, nested, configured, custom
# and multi_b.
custom_target(
  'check_headers',
  input: protos_gen.headers(),
  output: 'check_headers.stamp',
  command: [find_program('check_headers.py'), '@OUTPUT@', '5', '@INPUT@'],
  build_by_default: true,
)
