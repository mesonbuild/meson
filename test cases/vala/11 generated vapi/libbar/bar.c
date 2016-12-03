#include "bar.h"
#include "foo.h"

/**
 * bar_return_success:
 *
 * Returns 0
 */
int bar_return_success(void)
{
	return foo_return_success();
}
