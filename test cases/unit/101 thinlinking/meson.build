project('thinlinking', 'c')

hostsystem = host_machine.system()
archeck    = find_program(files('archeck.py'))
libthin    = static_library('thinlinked',    'file1.c', thin: true)
libfat     = static_library('fatlinked',     'file2.c', thin: false)
libthinpre = static_library('thinprelinked', 'file3.c', thin: true,  prelink: true)
libfatpre  = static_library('fatprelinked',  'file4.c', thin: false, prelink: true)
libmainpic = static_library('defpiclinked',  'main.c', pic: true)

exe = executable('testprog', [], link_with:
    [libthinpre, libthin, libfatpre,  libfat, libmainpic])

test('thinlinked', exe)

# On OS X and other systems, toolchains may not support thin-linking.
if hostsystem.contains('bsd') or hostsystem in ['dragonfly', 'linux']
  test('thin 1', archeck, args: ['thin', libthin])
  test('thin 2', archeck, args: ['thin', libthinpre])
endif
test('fat  1', archeck, args: ['fat',  libfat])
test('fat  2', archeck, args: ['fat',  libfatpre])
