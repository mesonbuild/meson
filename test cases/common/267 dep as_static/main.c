int libfunc1(void);
int libfunc2(void);
int libfunc3(void);
int libfunc4(void);

int main(void)
{
    int sum = libfunc1() + libfunc2() + libfunc3() + libfunc4();
    return sum == EXPECTED ? 0 : sum;
}
