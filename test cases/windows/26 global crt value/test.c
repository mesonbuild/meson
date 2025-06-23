#include <stdlib.h>
#include <stdio.h>
#include <io.h>
#include <crtdbg.h>

__declspec (dllimport)
int
liba_get_fd (void);

int
main (void)
{
  int fd_stderr = _fileno (stderr);
  if (fd_stderr >= 0)
    {
      _CrtSetReportMode (_CRT_ASSERT, _CRTDBG_MODE_FILE);
      _CrtSetReportFile (_CRT_ASSERT, (_HFILE)_get_osfhandle (fd_stderr));
    }

  int ret = _close (liba_get_fd ());
  if (ret != 0)
    return EXIT_FAILURE;

  return EXIT_SUCCESS;
}
