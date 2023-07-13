project('try compile', 'c', 'cpp')

code = '''#include<stdio.h>
void func(void) { printf("Something.\n"); }
'''

breakcode = '''#include<nonexisting.h>
void func(void) { printf("This won't work.\n"); }
'''

foreach lang : ['c', 'cpp']
  compiler = meson.get_compiler(lang)

  if compiler.compiles(code, name : 'code should succeed') == false
    error('Compiler ' + compiler.get_id() + ' is fail.')
  endif

  if compiler.compiles(files('valid.c'), name : 'file should succeed') == false
    error('Compiler ' + compiler.get_id() + ' is fail.')
  endif

  copied = configure_file(input: 'valid.c', output: lang + '-valid-copy.c', copy: true)
  if compiler.compiles(copied, name : 'built file should succeed') == false
    error('Compiler ' + compiler.get_id() + ' is fail.')
  endif

  if compiler.compiles(breakcode, name : 'code should fail')
    error('Compiler ' + compiler.get_id() + ' returned true on broken code.')
  endif

  if compiler.compiles(files('invalid.c'), name : 'file should fail')
    error('Compiler ' + compiler.get_id() + ' returned true on broken code.')
  endif
endforeach
