project('qt4 build test', 'cpp')

# This is a manual test rather than an automatic one
# because during Debian package builds only Qt4 or Qt5
# can be active.

qt4 = import('qt4')
qt4dep = dependency('qt4', modules : 'Gui')

prep = qt4.preprocess(moc_headers : ['mainWindow.h'], # These need to be fed through the moc tool before use. 
                      ui_files : 'mainWindow.ui',     # XML files that need to be compiled with the uic tol.
                      qresources : 'stuff.qrc',       # Resource file for rcc compiler.
)

q5exe = executable('qt4app',
sources : ['main.cpp', 'mainWindow.cpp', # Sources that don't need preprocessing.
prep],
dependencies : qt4dep)

# We need a console test application because some test environments
# do not have an X server.

qt4core = dependency('qt4', modules : 'Core')

qt4coreapp = executable('q4core', 'q4core.cpp',
dependencies : qt4core)

test('qt4test', qt4coreapp)

# The build system needs to include the cpp files from
# headers but the user must manually include moc
# files from sources.
manpreprocessed = qt4.preprocess(
    moc_sources : 'manualinclude.cpp',
    moc_headers : 'manualinclude.h')

q4maninclude = executable('q4maninclude',
sources : ['manualinclude.cpp', manpreprocessed],
dependencies : qt4core)

test('q4maninclude', q4maninclude)
