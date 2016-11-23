#include "symbol-underscore.h"

.text
.globl SYMBOL_NAME(square_unsigned)

SYMBOL_NAME(square_unsigned):
	mul	r1, r0, r0
	mov	r0, r1
	mov	pc, lr
