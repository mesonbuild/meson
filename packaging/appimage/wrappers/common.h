#pragma once

// Some global defines to enable functions
#define _XOPEN_SOURCE 500
#define _DEFAULT_SOURCE
#define _BSD_SOURCE
#define _GNU_SOURCE

extern int g_verbose;

#define LOG(fmt, ...)                                                          \
  if (g_verbose) {                                                             \
    printf(fmt "\n", ##__VA_ARGS__);                                           \
    fflush(stdout);                                                            \
  }

#define DIE(fmt, ...)                                                          \
  {                                                                            \
    fprintf(stderr, "\x1b[31;1mFATAL ERROR:\x1b[0;1m " fmt "\x1b[0m\n",        \
            ##__VA_ARGS__);                                                    \
    fflush(stderr);                                                            \
    exit(1);                                                                   \
  }

typedef struct AppRunInfo {
  char* appdir;
  char* appimage_path;
  char* meson_bin;
  char* python_bin;

  // basic path inf
  char* exe_path;
  char* path;
  char* ld_linux;
  char* pythonhome;
} AppRunInfo_t;

void info_autofill_paths(AppRunInfo_t* inf, const char* exe_name);

char* absolute_raw(const char* base, const char* relpath);
char* absolute(AppRunInfo_t* inf, const char* relpath);
void  envPrepend(const char* var, const char* val);

void logArgs(char** args);
