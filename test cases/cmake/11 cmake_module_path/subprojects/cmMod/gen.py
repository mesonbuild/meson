with open('main.c', 'w', encoding='utf-8') as fp:
  print('''
#include <stdio.h>

int main(void) {
  printf(\"Hello World\");
  return 0;
}
''', file=fp)
