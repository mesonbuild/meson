#include <stdint.h>
#include <cmTest.h>

#if __has_include(<private.h>) || __has_include(<private-system.h>)
#error CMake target-private include directories were exported
#endif

int main(void)
{
    cmTestFunc();
    return 0;
}

