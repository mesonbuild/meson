toplevel_proto = files('toplevel.proto')

configured_proto = configure_file(
  input: 'configured.proto.in',
  output: 'configured.proto',
  configuration: {'field_name': 'value'},
)

# A whole custom_target with a single output.
custom_proto = custom_target(
  'custom_proto',
  output: 'custom.proto',
  command: [gen_proto, '@OUTPUT@'],
)

# A custom_target in a child subdir with two outputs.
subdir('generated')

protos_gen = protoc.generate(
  toplevel_proto,
  files('nested/nested.proto'),
  configured_proto,
  custom_proto,
  # Only the second output: import name is 'generated/multi_b.proto'.
  generated_protos[1],
  toplevel_proto,  # passing the same file twice is allowed
  language: 'cpp',
  import_dirs: import_dir_inc,
  imports: imported_gen,
  install: true,
)
