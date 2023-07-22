project('prebuilt shared library', 'c')

search_dir = get_option('search_dir')
if search_dir == 'auto'
  search_dir = meson.current_source_dir()
elif search_dir == 'none'
  search_dir = []
endif

cc = meson.get_compiler('c')
shlib = cc.find_library('alexandria', dirs : search_dir)
shlibS = cc.find_library('alexandria', static : false, dirs : search_dir)

exe = executable('patron', 'patron.c', dependencies : shlib)
test('visitation', exe)
exeS = executable('shared_patron', 'patron.c',
  dependencies : shlibS)
test('shared visitation', exeS)

d = declare_dependency(dependencies : shlib)
dS = declare_dependency(dependencies : shlibS)

exe2 = executable('another_visitor', 'another_visitor.c',
  dependencies : d)
test('another', exe2)
exe2S = executable('shared_another_visitor', 'another_visitor.c',
  dependencies : dS)
test('shared another', exe2)

stlib = static_library(
  'rejected',
  'rejected.c',
  dependencies : shlib,
)
stlibS = static_library(
  'shared_rejected',
  'rejected.c',
  dependencies : shlibS,
)

rejected = executable(
  'rejected',
  'rejected_main.c',
  link_with : stlib,
)
test('rejected', rejected)
rejectedS = executable(
  'shared_rejected',
  'rejected_main.c',
  link_with : stlibS,
)
test('shared rejected', rejectedS)

rejected_whole = executable(
  'rejected_whole',
  'rejected_main.c',
  link_whole : stlib,
)
test('rejected (whole archive)', rejected_whole)
rejected_wholeS = executable(
  'shared_rejected_whole',
  'rejected_main.c',
  link_whole : stlibS,
)
test('shared rejected (whole archive)', rejected_wholeS)
