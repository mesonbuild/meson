#include "symbol-underscore.h"

.text
.globl SYMBOL_NAME(get_retval)

SYMBOL_NAME(get_retval):
	xorl	%eax, %eax
	retq
