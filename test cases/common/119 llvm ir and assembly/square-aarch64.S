#include "symbol-underscore.h"

#ifdef _MSC_VER

    AREA _TEXT, ARM64, CODE, READONLY

    EXPORT SYMBOL_NAME(square_unsigned)
SYMBOL_NAME(square_unsigned) PROC
    mul x1, x0, x0
    mov x0, x1
    ret
SYMBOL_NAME(square_unsigned) ENDP

    END

#else

#error gas syntax assembly for this test needs to be written

#endif
