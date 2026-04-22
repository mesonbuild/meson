project('demo', version: '1.0.0',
  default_options: [
    'python.bytecompile=-1',
    'python.purelibdir=/pure',
    'python.platlibdir=/plat',
  ]
)

py = import('python').find_installation()

# Static SBOM file installed via the helper.
install_data('component.cdx.json',
  install_dir: py.dist_info_install_dir('sboms'))

# Different subdir argument — same helper.
install_data('LICENSE.txt',
  install_dir: py.dist_info_install_dir('licenses'))

# custom_target with the helper as install_dir — exercises the dynamic
# code path that pandas / scipy / numpy use for build-time-generated
# SBOMs.
generated = custom_target('generated-sbom',
  output: 'generated.cdx.json',
  command: [py, '-c',
            'import sys; open(sys.argv[1], "w").write("{}")',
            '@OUTPUT@'],
  install: true,
  install_dir: py.dist_info_install_dir('sboms'))
