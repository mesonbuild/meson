#define MYDEF program
MYDEF foo
#ifdef CORRECT
        write (*,*) 'Hello, ' // 'world!'
#else
        write (*,*) 'Preprocessing failed!'
#endif
end MYDEF foo
