project('tryrun', 'c')

cc = meson.get_compiler('c')

ok_code = '''#include<stdio.h>
int main(int argc, char **argv) {
  printf("%s\n", "stdout");
  fprintf(stderr, "%s\n", "stderr");
  return 0;
}
'''

error_code = '''int main(int argc, char **argv) {
  return 1;
}
'''

no_compile_code = '''int main(int argc, char **argv) {
'''

ok = cc.run(ok_code)
err = cc.run(error_code)
noc = cc.run(no_compile_code)

if noc.compiled()
  error('Compilation fail test failed.')
else
  message('Fail detected properly.')
endif

if ok.compiled()
  message('Compilation worked.')
else
  error('Compilation did not work.')
endif

if ok.returncode() == 0
  message('Return code ok.')
else
  error('Return code fail')
endif

if err.returncode() == 1
  message('Bad return code ok.')
else
  error('Bad return code fail.')
endif

if ok.stdout().strip() == 'stdout'
  message('Stdout ok.')
else
  message('Bad stdout.')
endif

if ok.stderr().strip() == 'stderr'
  message('Stderr ok.')
else
  message('Bad stderr.')
endif
