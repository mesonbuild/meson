int shared_func(void);

int static_func(void) {
    return shared_func() + 1;
}
