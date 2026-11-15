#include <assert.h>
extern int f(void);
int main(void) { assert(f() == 21); }
