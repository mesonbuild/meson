project('install path',
  default_options: [
    'python.purelibdir=/pure',
    'python.platlibdir=/plat'
  ]
)

py = import('python').find_installation()
py.install_sources('test.py')
py.install_sources('test.py', pure: false)
