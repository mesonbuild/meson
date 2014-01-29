project('qt5 build test', 'cpp')

qt5dep = dependency('qt5', modules : 'Widgets')

q5exe = executable('qt5app',
sources : ['main.cpp', 'mainWindow.cpp'], # Sources that don't need preprocessing.
moc_headers : ['mainWindow.h'], # These need to be fed through the moc tool before use. 
ui_files : 'mainWindow.ui', # XML files that need to be compiled with the uic tol.
resources : 'stuff.qrc', # Resource file for rcc compiler.
deps : qt5dep)

# We need a console test application because some test environments
# do not have an X server.

q5core = executable('q5core', 'q5core.cpp',
deps : dependency('qt5', modules : 'Core'))

test('qt5test', q5core)
