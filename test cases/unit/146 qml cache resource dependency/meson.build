project('qml cache resource dependency', 'cpp', meson_version: '>= 1.7.0')

qt = import('qt6')
qtdep = dependency('qt6', modules: ['Core', 'Qml'], version: '>= 6.2', required: false)
if not qtdep.found() or not qt.has_tools(tools: ['qmlcachegen', 'rcc'], required: false)
  error('MESON_SKIP_TEST Qt6 QML tools not found')
endif

sources = qt.qml_module(
  'MyModule',
  qml_sources: files('Main.qml'),
  generate_qmltype: false,
  resources_prefix: get_option('resource_prefix'),
)

# Only build the generated sources: compiling them would require Qt's private headers.
static_library('cache', sources, name_prefix: '', name_suffix: 'a', dependencies: qtdep)
