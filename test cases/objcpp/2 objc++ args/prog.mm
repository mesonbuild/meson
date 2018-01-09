#import<stdio.h>

class TestClass
{
};

int main(int argc, char **argv)
{
#ifdef MESON_OBJCPP_TEST
int x = 1;
#endif

  printf("x = %x\n", x);

  return 0;
}
