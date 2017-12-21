#include <stdlib.h>

#include "platform/platform.h"
#include "SDK/sdk.h"

int main() {
    return platform_function() + sdk_function() == 3 ? EXIT_SUCCESS : EXIT_FAILURE;
}
