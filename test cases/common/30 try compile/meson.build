project('try compile', 'c', 'cpp')

code = '''#include<stdio.h>
void func() { printf("Something.\n"); }
'''

breakcode = '''#include<nonexisting.h>
void func() { printf("This won't work.\n"); }
'''

foreach compiler : [meson.get_compiler('c'), meson.get_compiler('cpp')]
  if compiler.compiles(code, name : 'should succeed') == false
    error('Compiler ' + compiler.get_id() + ' is fail.')
  endif

  if compiler.compiles(files('valid.c'), name : 'should succeed') == false
    error('Compiler ' + compiler.get_id() + ' is fail.')
  endif

  if compiler.compiles(breakcode, name : 'should fail')
    error('Compiler ' + compiler.get_id() + ' returned true on broken code.')
  endif

  if compiler.compiles(files('invalid.c'), name : 'should fail')
    error('Compiler ' + compiler.get_id() + ' returned true on broken code.')
  endif
endforeach
