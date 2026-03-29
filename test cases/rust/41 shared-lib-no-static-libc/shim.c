extern void hello(void);

void shim_hello(void) {
    hello();
}
