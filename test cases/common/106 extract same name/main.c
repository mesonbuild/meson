int func1();
int func2();

int main(void) {
    return !(func1() == 23 && func2() == 42);
}
