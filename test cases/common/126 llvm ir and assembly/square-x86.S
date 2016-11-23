#include "symbol-underscore.h"

.text
.globl SYMBOL_NAME(square_unsigned)

SYMBOL_NAME(square_unsigned):
	movl	4(%esp), %eax
	imull	%eax, %eax
	retl
