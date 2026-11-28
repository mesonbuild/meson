subdir('generated')

imported_gen = protoc.generate(
  files('imported.proto'),
  imported_generated_proto,
  language: 'cpp',
  # Passed after the args from codegen.protoc(), so this one wins.
  args: '--error_format=msvs',
  install: true,
)
