project('qt5 build test', 'cxx')

qt5dep = find_dep('qt5', modules : 'Widgets', required : true)

q5exe = executable('qt5test',
sources : ['main.cpp', 'mainWindow.cpp'], # Sources that don't need preprocessing.
moc_headers : ['mainWindow.h'], # These need to be fed through the moc tool before use. 
ui_files : 'mainWindow.ui', # XML files that need to be compiled with the uic tol.
deps : qt5dep)

add_test('qt5test', q5exe)
