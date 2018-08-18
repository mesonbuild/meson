int func1();
int func2();

int main(int argc, char **argv) {
    return !(func1() == 23 && func2() == 42);
}
