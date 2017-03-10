project('compute int', 'c', 'cpp')

inc = include_directories('.')

# Test with C
cc = meson.get_compiler('c')

intsize = cc.compute_int('sizeof(int)', low : 1, high : 16, guess : 4)
foobar = cc.compute_int('FOOBAR_IN_FOOBAR_H', prefix : '#include "foobar.h"', include_directories : inc)

cd = configuration_data()
cd.set('INTSIZE', intsize)
cd.set('FOOBAR', foobar)
cd.set('CONFIG', 'config.h')
configure_file(input : 'config.h.in', output : 'config.h', configuration : cd)
s = configure_file(input : 'prog.c.in', output : 'prog.c', configuration : cd)

e = executable('prog', s)
test('compute int test', e)

# Test with C++
cpp = meson.get_compiler('cpp')

intsize = cpp.compute_int('sizeof(int)')
foobar = cpp.compute_int('FOOBAR_IN_FOOBAR_H', prefix : '#include "foobar.h"', include_directories : inc)

cdpp = configuration_data()
cdpp.set('INTSIZE', intsize)
cdpp.set('FOOBAR', foobar)
cdpp.set('CONFIG', 'config.hpp')
configure_file(input : 'config.h.in', output : 'config.hpp', configuration : cdpp)
spp = configure_file(input : 'prog.c.in', output : 'prog.cc', configuration : cdpp)

epp = executable('progpp', spp)
test('compute int test c++', epp)
