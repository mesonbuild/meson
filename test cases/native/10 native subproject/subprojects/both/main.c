#ifndef GLOBAL_CROSS_BUILD
#error "add_global_arguments() was not applied"
#endif

#if GLOBAL_CROSS_BUILD != EXPECTED_CROSS_BUILD
#error "add_global_arguments() was applied for the wrong machine"
#endif

int main(void) {
    return 0;
}
