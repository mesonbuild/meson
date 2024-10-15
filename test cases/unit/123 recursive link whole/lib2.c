int lib1(void);
int libsub(void);

int lib2(void) { return lib1() + libsub(); }
