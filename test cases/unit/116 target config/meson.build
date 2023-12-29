project('target config', 'c', default_options: ['python.target_config=config.toml'])

py_mod = import('python')
py = py_mod.find_installation()

if py.language_version() != '3.0.3'
  error('Wrong Python version, expecting 3.0.3 but got', py.language_version())
endif

