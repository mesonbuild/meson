#include "common.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// Assume that IS_PYTHON_SCRIPT is either 0 or 1
#ifndef IS_PYTHON_SCRIPT
#define IS_PYTHON_SCRIPT 0
#endif

#ifndef STATICALLY_LINKED
#define STATICALLY_LINKED 0
#endif

int main(int argc, char* argv[]) {
  AppRunInfo_t info;
  char*        args[argc + 3];
  int          counter;

  g_verbose = 0;

  memset(&info, 0, sizeof(info));
  memset(&args, 0, sizeof(args));

  // Check for verbose output
  char* verbose = getenv("VERBOSE");
  if (verbose && verbose[0] != '0') {
    g_verbose = 1;
  }

  info_autofill_paths(&info, REAL_EXE);

  LOG("Meson exe wrapper " APPRUN_VERSION);
  LOG("Running " REAL_EXE);
  LOG("Extracted AppDir:  %s", info.appdir);
  LOG("Real exe location: %s", info.exe_path);
  LOG("PATH fragment:     %s", info.path);
  LOG("Is Python script:  %d", IS_PYTHON_SCRIPT);
  LOG("Statically linked: %d", STATICALLY_LINKED);

  // Set the commandline arguments for exeve
  // Again, IS_PYTHON_SCRIPT and STATICALLY_LINKED must be either 0 or 1
  counter = 2 + IS_PYTHON_SCRIPT - STATICALLY_LINKED;
  for (int i = 1; i < argc; i++) {
    args[counter++] = argv[i];
  }

  args[counter++] = NULL;

#if IS_PYTHON_SCRIPT
  args[0] = info.ld_linux;
  args[1] = absolute(&info, "usr/bin/python3");
  args[2] = info.exe_path;
#elif STATICALLY_LINKED
  args[0] = info.exe_path;
#else
  args[0] = info.ld_linux;
  args[1] = info.exe_path;
#endif

  // Set the env vars
  envPrepend("PATH", info.path);
  setenv("PYTHONHOME", info.pythonhome, 1);
  setenv("MESON_COMMAND", info.meson_bin, 1);
  setenv("MESON_PYTHON_BIN", info.python_bin, 1);
  putenv("PYTHONDONTWRITEBYTECODE=1");

  logArgs(args);

  if (execv(args[0], args) != 0) {
    DIE("execv failed");
  }

  // We are technically leaking memory here, but all memory is freed once the
  // program exits anyway...
  return 0;
}
