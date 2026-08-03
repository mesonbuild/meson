extern int x1(void);
extern int x2(void);
int x3(void) { return x2() + x1(); }
