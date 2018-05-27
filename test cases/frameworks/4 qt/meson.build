project('qt4 and 5 build test', 'cpp',
  # Qt5 now requires C++ 11 support
  default_options : ['cpp_std=c++11'])

qt5_modules = ['Widgets']
foreach qt : ['qt4', 'qt5']
  qt_modules = ['Core', 'Gui']
  if qt == 'qt5'
    qt_modules += qt5_modules
  endif

  # Test that invalid modules are indeed not found
  fakeqtdep = dependency(qt, modules : ['DefinitelyNotFound'], required : false, method : get_option('method'))
  if fakeqtdep.found()
    error('Invalid qt dep incorrectly found!')
  endif

  # Test that partially-invalid modules are indeed not found
  fakeqtdep = dependency(qt, modules : ['Core', 'DefinitelyNotFound'], required : false, method : get_option('method'))
  if fakeqtdep.found()
    error('Invalid qt dep incorrectly found!')
  endif

  # This test should be skipped if qt5 isn't found
  if qt == 'qt5'
    dep = dependency(qt, modules : ['Core'], required : false, method : get_option('method'))
    if not dep.found()
      error('MESON_SKIP_TEST qt5 not found.')
    endif
  endif

  # Ensure that the "no-Core-module-specified" code branch is hit
  nocoredep = dependency(qt, modules : ['Gui'], required : qt == 'qt5', method : get_option('method'))

  # If qt4 modules are found, test that. qt5 is required.
  qtdep = dependency(qt, modules : qt_modules, private_headers: true, required : qt == 'qt5', method : get_option('method'))
  if qtdep.found()
    qtmodule = import(qt)

    # The following has two resource files because having two in one target
    # requires you to do it properly or you get linker symbol clashes.

    prep = qtmodule.preprocess(
      moc_headers : ['mainWindow.h'],           # These need to be fed through the moc tool before use. 
      ui_files : 'mainWindow.ui',               # XML files that need to be compiled with the uic tol.
      method : get_option('method')
    )

    # Resource file(s) for rcc compiler
    extra_cpp_args = []
    if meson.is_unity()
      extra_cpp_args += '-DUNITY_BUILD'
      prep_rcc = qtmodule.preprocess(qt + '_unity_ressource', qresources : ['stuff.qrc', 'stuff2.qrc'], method : get_option('method'))
    else
      prep_rcc = qtmodule.preprocess(qresources : ['stuff.qrc', 'stuff2.qrc'], method : get_option('method'))
    endif

    # Test that setting a unique name with a positional argument works
    qtmodule.preprocess(qt + 'teststuff', qresources : files(['stuff.qrc', 'stuff2.qrc']), method : get_option('method'))

    qexe = executable(qt + 'app',
      sources : ['main.cpp', 'mainWindow.cpp', # Sources that don't need preprocessing.
      prep, prep_rcc],
      dependencies : qtdep,
      cpp_args: extra_cpp_args)

    # We need a console test application because some test environments
    # do not have an X server.

    translations = qtmodule.compile_translations(ts_files : qt+'core_fr.ts', build_by_default : true)

    qtcore = dependency(qt, modules : 'Core', method : get_option('method'))

    qtcoreapp = executable(qt + 'core', 'q5core.cpp',
      dependencies : qtcore)

    test(qt + 'test', qtcoreapp)

    # The build system needs to include the cpp files from
    # headers but the user must manually include moc
    # files from sources.
    manpreprocessed = qtmodule.preprocess(
      moc_extra_arguments : ['-DMOC_EXTRA_FLAG'], # This is just a random macro to test `moc_extra_arguments`
      moc_sources : 'manualinclude.cpp',
      moc_headers : 'manualinclude.h',
      method : get_option('method'))

    qtmaninclude = executable(qt + 'maninclude',
      sources : ['manualinclude.cpp', manpreprocessed],
      dependencies : qtcore)

    test(qt + 'maninclude', qtmaninclude)

    # building Qt plugins implies to give include path to moc
    plugin_includes = include_directories('pluginInterface', 'plugin')
    pluginpreprocess = qtmodule.preprocess(
      moc_headers : 'plugin/plugin.h',
      include_directories : plugin_includes
    )
    plugin = library(qt + 'plugin', 'plugin/plugin.cpp', pluginpreprocess,
          include_directories : plugin_includes,
          dependencies : qtcore)
    if qt == 'qt5'
      subdir('subfolder')
    endif
  endif
endforeach
