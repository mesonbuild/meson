project('test_c_std','c')
#
# Test GCC or Clang for all values of c_std which
# the native compiler version and Meson support.
#
co = meson.get_compiler('c')
cid = co.get_id()
c_version = co.version()
message('Compiler is ' + cid + ' ' + c_version)
c_stds = []
g_stds = []
if cid == 'gcc'
    c_stds = ['c89','c99','c11']
    g_stds = ['gnu89','gnu99','gnu11']
    if c_version.version_compare('>=8.0.0')
        c_stds += ['c17','c18']
        g_stds += ['gnu17','gnu18']
    endif
elif cid == 'clang'
    c_stds = ['c89','c99','c11']
    g_stds = ['gnu89','gnu99','gnu11']
    if c_version.version_compare('>=7.0.0')
        c_stds += ['c17']
        g_stds += ['gnu17']
    endif
endif
stds = c_stds + g_stds
foreach std : stds
    message('Testing '+cid+' -std='+std)
    e = executable('test-'+cid+'-'+std, 'read_env.c',
        override_options : ['c_std='+std])
    test('Test '+cid+' -std='+std, e,
        env : ['_compiler='+cid,'_std='+std])
endforeach
