#include<thread>
#include<cstdio>

void main_func() {
    printf("Printing from a thread.\n");
}

int main(int, char**) {
    printf("Starting thread.\n");
    std::thread th(main_func);
    th.join();
    printf("Stopped thread.\n");
    return 0;
}
