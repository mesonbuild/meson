project('qt5 build test', 'cxx')

qt5dep = find_dep('qt5', modules : 'Widgets', required : true)

q5exe = executable('qt5test',
sources : ['main.cpp', 'mainWindow.cpp'],
moc_headers : ['mainWindow.h'],
ui_files : 'mainWindow.ui',
deps : qt5dep)

add_test('qt5test', q5exe)
