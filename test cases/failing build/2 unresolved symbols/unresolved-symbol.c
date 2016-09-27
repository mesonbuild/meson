void some_unresolved_symbol(void);

int
#ifdef EXECUTABLE
main(void)
#else
do_stuff(void)
#endif
{
  some_unresolved_symbol();
  return 0;
}
