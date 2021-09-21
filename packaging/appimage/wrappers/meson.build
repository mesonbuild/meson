project('apprun', ['c'],
  default_options: [
    'warning_level=3',
    'optimization=s',
    'werror=true',
    'debug=false',
    'strip=true',
    'b_lto=true',
    'prefix=/',
  ],
  version: '1.0',
)

fakebin_dir = 'fakebin'
c_flags = [
  '-Wno-pedantic',
  '-DAPPRUN_VERSION="@0@"'.format(meson.project_version()),
  '-DFAKEBIN="@0@"'.format(fakebin_dir),
]
link_flags = ['-static']

common = static_library('common', ['common.c'], c_args : c_flags)

wrappers = {
  'meson': ['-DIS_PYTHON_SCRIPT=1'],
  'ninja': [],
  #'cmake': [],
  'pkgconf': [],
  'python': [],
  'python3': [],
  'python3.9': [],
}

foreach name, extra_flags : wrappers
  base_flags = ['-DREAL_EXE="' + name + '"']

  executable(name, ['wrapper.c'],
    link_with:   [common],
    c_args:      c_flags + base_flags + extra_flags,
    link_args:   link_flags,
    install:     true,
    install_dir: fakebin_dir
  )
endforeach
