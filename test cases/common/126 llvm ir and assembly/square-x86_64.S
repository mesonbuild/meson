#include "symbol-underscore.h"

#ifdef _MSC_VER /* MSVC on Windows */

PUBLIC SYMBOL_NAME(square_unsigned)
_TEXT   SEGMENT

SYMBOL_NAME(square_unsigned) PROC
        mov     eax, ecx
	imul	eax, eax
	ret
SYMBOL_NAME(square_unsigned) ENDP

_TEXT   ENDS
END

#else

.text
.globl SYMBOL_NAME(square_unsigned)

# ifdef _WIN32 /* MinGW */
SYMBOL_NAME(square_unsigned):
	imull	%ecx, %ecx
	movl	%ecx, %eax
	retq
# else /* Linux and OS X */
SYMBOL_NAME(square_unsigned):
	imull	%edi, %edi
	movl	%edi, %eax
	retq
# endif

#endif
