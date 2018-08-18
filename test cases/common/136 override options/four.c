int func();

static int duplicate_func() {
    return -4;
}

int main(int argc, char **argv) {
    return duplicate_func() + func();
}
