project('try compile', 'c')

code = '''#include<stdio.h>
void func() { printf("Something.\n"); }
'''

breakcode = '''#include<nonexisting.h>
void func() { printf("This won't work.\n"); }
'''

compiler = meson.get_compiler('c')
if compiler.compiles(code, name : 'should succeed') == false
  error('Compiler is fail.')
endif

if compiler.compiles(breakcode, name : 'should fail')
  error('Compiler returned true on broken code.')
endif
