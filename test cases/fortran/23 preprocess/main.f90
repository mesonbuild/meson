#define MYDEF program
MYDEF foo
    character(20) :: str
#ifdef CORRECT
        str = 'Hello, ' // 'world!'
#else
        str = 'Preprocessing error!'
#endif
    if (str /= 'Hello, world!') then
        print *, 'Preprocessing failed.'
        error stop 1
    end if
    stop 0
end MYDEF foo
