project('qt5 build test', 'cpp')

qt5 = import('qt5')
qt5dep = dependency('qt5', modules : ['Core', 'Gui', 'Widgets'])

# The following has two resource files because having two in one target
# requires you to do it properly or you get linker symbol clashes.

prep = qt5.preprocess(
  moc_headers : ['mainWindow.h'],           # These need to be fed through the moc tool before use. 
  ui_files : 'mainWindow.ui',               # XML files that need to be compiled with the uic tol.
  qresources : ['stuff.qrc', 'stuff2.qrc'], # Resource file for rcc compiler.
)

q5exe = executable('qt5app',
  sources : ['main.cpp', 'mainWindow.cpp', # Sources that don't need preprocessing.
  prep],
  dependencies : qt5dep)

# We need a console test application because some test environments
# do not have an X server.

qt5core = dependency('qt5', modules : 'Core')

qt5coreapp = executable('q5core', 'q5core.cpp',
  dependencies : qt5core)

test('qt5test', qt5coreapp)

# The build system needs to include the cpp files from
# headers but the user must manually include moc
# files from sources.
manpreprocessed = qt5.preprocess(
  moc_sources : 'manualinclude.cpp',
  moc_headers : 'manualinclude.h')

q5maninclude = executable('q5maninclude',
  sources : ['manualinclude.cpp', manpreprocessed],
  dependencies : qt5core)

test('q5maninclude', q5maninclude)
