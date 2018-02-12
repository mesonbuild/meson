extern "C" int foo();

int main(int, char**) {
    return foo() != 42;
}
