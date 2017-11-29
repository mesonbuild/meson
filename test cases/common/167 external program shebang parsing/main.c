#include <stdio.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <sys/types.h>

#ifdef _WIN32
 #include <io.h>
 #include <windows.h>
#else
 #include <unistd.h>
#endif

static int
intrp_copyfile (char * src, char * dest)
{
#ifdef _WIN32
  if (!CopyFile (src, dest, FALSE))
    return 1;
  return 0;
#else
  return execlp ("cp", "copyfile", src, dest, NULL);
#endif
}

static char*
parser_get_line (FILE * f)
{
  ssize_t size;
  size_t n = 0;
  char *line = NULL;

  size = getline (&line, &n, f);
  if (size < 0) {
    fprintf (stderr, "%s\n", strerror (errno));
    free (line);
    return NULL;
  }
  return line;
}

int
main (int argc, char * argv[])
{
  FILE *f;
  char *line = NULL;

  if (argc != 4) {
    fprintf (stderr, "Invalid number of arguments: %i\n", argc);
    goto err;
  }

  if ((f = fopen (argv[1], "r")) == NULL) {
    fprintf (stderr, "%s\n", strerror (errno));
    goto err;
  }

  line = parser_get_line (f);

  if (!line || line[0] != '#' || line[1] != '!') {
    fprintf (stderr, "Invalid script\n");
    goto err;
  }

  free (line);
  line = parser_get_line (f);

  if (!line || strncmp (line, "copy", 4) != 0) {
    fprintf (stderr, "Syntax error\n");
    goto err;
  }

  return intrp_copyfile (argv[2], argv[3]);

err:
  free (line);
  return 1;
}
