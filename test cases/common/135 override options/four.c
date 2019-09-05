int func();

static int duplicate_func() {
    return -4;
}

int main() {
    return duplicate_func() + func();
}
