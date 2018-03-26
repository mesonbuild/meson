cfg = configuration_data()

cfg.set('filepath', meson.current_source_dir()+'/../thing2.png')
rc_file = configure_file(
  configuration : cfg,
  input : 'resources/stuff4.qrc.in',
  output : 'stuff4.qrc',
)

extra_cpp_args = []
if meson.is_unity()
  extra_cpp_args += '-DUNITY_BUILD'
  qresources = qtmodule.preprocess(qt + '_subfolder_unity_ressource',qresources : ['resources/stuff3.qrc', rc_file])
else
  qresources = qtmodule.preprocess(qresources : ['resources/stuff3.qrc', rc_file])
endif

app = executable('subfolder', 'main.cpp', qresources, dependencies : qtdep, cpp_args: extra_cpp_args)
test(qt + 'subfolder', app)
