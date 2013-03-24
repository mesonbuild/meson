#include<boost/utility.hpp>

class MyClass : boost::noncopyable {
private:
    int x;

public:
    MyClass() {
        x = 44;
    }

    int getValue() const { return x; }
};

int main(int argc, char **argv) {
    MyClass foo;
    if(foo.getValue() == 44)
        return 0;
    return 1;
}
