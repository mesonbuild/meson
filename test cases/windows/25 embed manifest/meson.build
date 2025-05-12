project('can-manifests-be-embedded', 'c')

cc = meson.get_compiler('c')

if cc.get_linker_id() not in ['link', 'lld-link', 'xilink'] # cc.get_linker_argument_syntax() != 'link'
  error('MESON_SKIP_TEST: test is only relevant for the Microsoft linker')
endif

# Ensure that the manifest can be embedded
executable('prog', 'prog.c',
  link_args: ['/MANIFEST:EMBED', '/MANIFESTINPUT:' + meson.project_source_root() / 'DPIAware.manifest'])
