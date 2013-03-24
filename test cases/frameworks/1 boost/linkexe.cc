#include<boost/thread.hpp>

struct callable {
    void operator()() {};
};

int main(int argc, char **argv) {
    callable x;
    boost::thread thr(x);
    thr.join();
    return 0;
}
