int func();

static int duplicate_func() {
    return -4;
}

int main(void) {
    return duplicate_func() + func();
}
