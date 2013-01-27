int main(int argc, char **argv) {
    int ptrsize = sizeof(void*);
    int expsize;
#ifdef IS64
    expsize = 8;
#else
    expsize = 4;
#endif
    return ptrsize == expsize ? 0 : 1;
}
