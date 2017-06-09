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

  # Ensure that the "no-Core-module-specified" code branch is hit
  nocoredep = dependency(qt, modules : ['Gui'], required : qt == 'qt5', method : get_option('method'))

  # If qt4 modules are found, test that. qt5 is required.
  qtdep = dependency(qt, modules : qt_modules, required : qt == 'qt5', method : get_option('method'))
  if qtdep.found()
    qtmodule = import(qt)

    # The following has two resource files because having two in one target
    # requires you to do it properly or you get linker symbol clashes.

    prep = qtmodule.preprocess(
      moc_headers : ['mainWindow.h'],           # These need to be fed through the moc tool before use. 
      ui_files : 'mainWindow.ui',               # XML files that need to be compiled with the uic tol.
      qresources : ['stuff.qrc', 'stuff2.qrc'], # Resource file for rcc compiler.
      method : get_option('method')
    )

    # Test that setting a unique name with a positional argument works
    qtmodule.preprocess(qt + 'teststuff', qresources : ['stuff.qrc'], method : get_option('method'))

    qexe = executable(qt + 'app',
      sources : ['main.cpp', 'mainWindow.cpp', # Sources that don't need preprocessing.
      prep],
      dependencies : qtdep)

    # We need a console test application because some test environments
    # do not have an X server.

    qtcore = dependency(qt, modules : 'Core', method : get_option('method'))

    qtcoreapp = executable(qt + 'core', 'q5core.cpp',
      dependencies : qtcore)

    test(qt + 'test', qtcoreapp)

    # The build system needs to include the cpp files from
    # headers but the user must manually include moc
    # files from sources.
    manpreprocessed = qtmodule.preprocess(
      moc_sources : 'manualinclude.cpp',
      moc_headers : 'manualinclude.h',
      method : get_option('method'))

    qtmaninclude = executable(qt + 'maninclude',
      sources : ['manualinclude.cpp', manpreprocessed],
      dependencies : qtcore)

    test(qt + 'maninclude', qtmaninclude)
  endif
endforeach
