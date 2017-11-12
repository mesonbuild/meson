protos_subdir_files = [
  'messages/bits/dummy_enum.proto',
  'messages/dummy_messages2.proto',
  'dummy_service2.proto',
]
protos_subdir_src = []
protos_subdir_hdr = []
foreach p : protos_subdir_files
  cc_target = custom_target(
    p.underscorify(),
    input: p,
    output: ['@ROOTNAME@.pb.cc', '@ROOTNAME@.pb.h'],
    command: [protoc, '-I', '@CURRENT_SOURCE_DIR@', '--cpp_out', '@OUTDIR@', '@INPUT@']
  )
  protos_subdir_src += cc_target[0]
  protos_subdir_hdr += cc_target[1]
endforeach
