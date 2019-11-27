#include <iostream>

// MSVC-specific compilation test; code compiled with /ZI 
// cannot use __LINE__ as a non-type template argument
template<unsigned line_num> void print_line()
{
    std::cout << "Line #" << line_num << std::endl;
}

int main() {
    print_line<__LINE__>();
}
