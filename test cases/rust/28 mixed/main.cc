#include <iostream>

extern "C" void hello_rust(void);

int main() { std::cout << "This is C++!\n"; hello_rust(); }
