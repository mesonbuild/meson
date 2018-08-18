project('default library', 'cpp')

flib = library('ef', 'ef.cpp')
exe = executable('eftest', 'eftest.cpp', link_with : flib)
test('eftest', exe)
