#include "common.h"

#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int g_verbose;

void info_autofill_paths(AppRunInfo_t* info, const char* exe_name) {
  if (!info) {
    DIE("invalid argument to info_autofill_paths");
  }

  if (!info->appdir && exe_name) {
    // First sanity check that we are run in an environment set by AppRun
    info->appdir = getenv("APPDIR");
    if (!info->appdir) {
      LOG("Wrapper %s run without AppRun", exe_name);
      info->appdir = dirname(realpath("/proc/self/exe", NULL));

      // Calculate the appdir root
      int components = 1;
      for (const char* c = FAKEBIN; *c; c++) {
        if (*c == '/') {
          components++;
        }
      }

      for (int i = 0; i < components; i++) {
        info->appdir = dirname(info->appdir);
      }
    }
  }

  if (!info->appdir) {
    DIE("info->appdir was not set or could not be computed");
  }

  info->path       = absolute(info, FAKEBIN);
  info->meson_bin  = absolute(info, FAKEBIN "/meson");
  info->python_bin = absolute(info, FAKEBIN "/python");
  info->ld_linux   = absolute(info, "usr/lib/ld-linux.so");
  info->pythonhome = absolute(info, "usr");

  if (exe_name) {
    char* bin_dir  = absolute(info, "usr/bin");
    info->exe_path = absolute_raw(bin_dir, exe_name);
    free(bin_dir);
  }
}

void logArgs(char** args) {
  if (!g_verbose) {
    return;
  }

  int counter = 0;
  printf("\nArguments:\n");
  counter = 0;
  while (1) {
    if (!args[counter]) {
      break;
    }
    printf(" %2d: %s\n", counter, args[counter]);
    counter++;
  }

  printf("\n");
  fflush(stdout);
}

char* absolute_raw(const char* base, const char* relpath) {
  const size_t absLen = strlen(base) + strlen(relpath) + 2;
  char*        abs    = malloc(sizeof(char) * absLen);
  snprintf(abs, absLen, "%s/%s", base, relpath);
  return abs;
}

char* absolute(AppRunInfo_t* info, const char* relpath) {
  return absolute_raw(info->appdir, relpath);
}

void envPrepend(const char* var, const char* val) {
  char* curr = getenv(var);
  if (!curr) {
    setenv(var, val, 1);
    return;
  }

  const size_t len = strlen(var) + strlen(val) + strlen(curr) + 3;
  char*        res = malloc(sizeof(char) * len);
  snprintf(res, len, "%s=%s:%s", var, val, curr);
  putenv(res);
}
