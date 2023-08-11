#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
  char **args = calloc(argc + 1, sizeof(char *));
  const char *file = NULL;
  int nargs = 1;
  for (int i = 1; i < argc; i++) {
    if (strcmp(argv[i], "--notify") == 0) {
        file = argv[i + 1];
        i++;
    } else {
        args[nargs++] = argv[i];
    }
  }
  args[0] = "rustc";
  args[nargs] = NULL;

  if (file == NULL) {
    printf("Could not find --notify argument\n");
    exit(1);
  }

  int infd[2];
  pipe(infd);

  pid_t child = fork();

  if(!child) {
    close(STDERR_FILENO);
    dup2(infd[1], STDERR_FILENO);
    close(infd[0]);
    close(infd[1]);
    execvp(args[0], args);
  } else {
    close(infd[1]);

    int fd = open(file, O_WRONLY);

    while (1) {
      char input[10000];
      ssize_t len = read(infd[0], input, sizeof(input));
      if (len <= 0) {
          int status;
          waitpid(child, &status, 0);
          return status != 0 ? 1 : 0;
      }
      input[len] = '\0';
      const char *prefix = "{\"artifact\":\"";
      size_t prefix_len = strlen(prefix);
      if (len > prefix_len && strncmp(input, prefix, prefix_len) == 0) {
        char *path = input + prefix_len;
        char *p = strchr(path, '"');
        p[0] = '\n';
        write(fd, path, p - path + 1);
        fsync(fd);
      }
    }
  }
}
