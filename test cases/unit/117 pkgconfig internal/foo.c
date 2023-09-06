int public(void);
int private(void);
int internal(void);
int internal2(void);

int foo(void) {
    return public() + private() + internal() + internal2();
}
