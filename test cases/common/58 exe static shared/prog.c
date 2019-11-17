int shlibfunc2();
int statlibfunc();

int main(void) {
    if (statlibfunc() != 42)
        return 1;
    if (shlibfunc2() != 24)
        return 1;
    return 0;
}
