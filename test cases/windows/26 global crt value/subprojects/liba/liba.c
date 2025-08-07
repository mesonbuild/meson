#include <stdlib.h>
#include <fcntl.h>
#include <io.h>
#include <assert.h>

__declspec (dllexport)
int
liba_get_fd (void)
{
  int ret;

  int fd = _open ("NUL", _O_BINARY | _O_NOINHERIT | _O_WRONLY, 0);
  assert (fd >= 0);

  if (_dup2 (fd, 500) != 0)
    exit (77); /* skip */

  ret = _close (fd);
  assert (ret == 0);

  return 500;
}
