#include "symbol-underscore.h"

.text
.globl SYMBOL_NAME(square_unsigned)

SYMBOL_NAME(square_unsigned):
	imull	%edi, %edi
	movl	%edi, %eax
	retq
