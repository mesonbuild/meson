int libshared(void);
int libwhole(void);

int lib1(void) { return 42 + libshared() + libwhole(); }
