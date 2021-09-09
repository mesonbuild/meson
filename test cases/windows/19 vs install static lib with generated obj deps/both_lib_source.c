extern int static_lib_function(void);

int both_lib_function(void)
{
    return static_lib_function();
}
