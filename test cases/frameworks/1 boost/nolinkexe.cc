#include<boost/utility.hpp>

class MyClass : boost::noncopyable {
public:
    MyClass() {};
    ~MyClass() {};
};

int main(int argc, char **argv) {
    MyClass obj;
    return 0;
}
