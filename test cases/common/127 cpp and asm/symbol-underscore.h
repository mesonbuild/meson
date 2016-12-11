#if defined(__WIN32__) || defined(__APPLE__)
# define SYMBOL_NAME(name) _##name
#else
# define SYMBOL_NAME(name) name
#endif
