// SPDX-license-identifier: Apache-2.0

#define _DEFAULT_SOURCE
#include <features.h>

#include <stdio.h>
#include <libruntime.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <inttypes.h>

#include "runtime-config.h"

#if VERBOSE
#define LOG(fmt, ...)                                                                                                  \
    {                                                                                                                  \
        printf(fmt "\n", ##__VA_ARGS__);                                                                               \
        fflush(stdout);                                                                                                \
    }
#else
#define LOG(fmt, ...)
#endif

#define CHECK_OPT(opt) ((strlen(argv[i]) > 10) && (strcmp(opt, argv[i] + 10) == 0))

void print_help() {
    printf("Meson portable runtime " RUNTIME_VERSION " (based on AppImage)\n"
           "\n"
           "Runtime specific options:\n"
           "  --runtime-help                 Print this help message and exit\n"
           "  --runtime-version              Print the runtime version (NOT the Meson version) and exit\n"
           "  --runtime-info                 Print runime information and exit\n"
           "  --runtime-setup   <BUILD DIR>  Set up the <BUILD DIR>/meson-runtime directory and exit\n"
           "\n");
}

void print_info(appimage_context_t *context) {
    printf("Meson runtime information:\n"
           "  - detected runtime path: %s\n"
           "  - squashfs offset:       %" PRId64 "\n",
           context->appimage_path,
           (int64_t)context->fs_offset);
}

bool setup_build_dir(appimage_context_t *context, const char *build_dir) {
    bool         ret     = true;
    FILE *       fp      = NULL;
    const size_t max_len = strlen(build_dir) + 32; // enough to add '/meson-runtime/runtime-id.txt'
    char *       prefix  = malloc(sizeof(char) * (max_len + 1));
    snprintf(prefix, max_len, "%s/meson-runtime", build_dir);
    LOG("Setting up runtime dir %s", prefix);

    ret = appimage_self_extract(context, prefix, NULL, true, false);
    if (!ret) {
        fprintf(stderr, "Failed to self-extract squashfs filesystem.\n");
        goto cleanup;
    }

    // Write build ID
    strcat(prefix, "/runtime-id.txt");
    fp = fopen(prefix, "w");
    if (fp == NULL) {
        perror("Failed to open runtime-id.txt");
        ret = false;
        goto cleanup;
    }
    fprintf(fp, "%s", BUILD_ID);

cleanup:
    if (fp != NULL) {
        fclose(fp);
    }
    free(prefix);
    return ret;
}

char *check_existing_runtime(const char *build_dir) {
    const size_t max_len = strlen(build_dir) + 32;
    char *       id_txt  = malloc(sizeof(char) * (max_len + 1));
    char         UUID[37];
    snprintf(id_txt, max_len, "%s/meson-runtime/runtime-id.txt", build_dir);

    LOG("Checking possible meson-runtime %s", id_txt);

    // Check if the file exists
    if (access(id_txt, F_OK) != 0) {
        LOG("meson-runtime %s does not exist", id_txt);
        free(id_txt);
        return NULL;
    }

    // Check that we have the correct version
    FILE *fp = fopen(id_txt, "r");
    if (!fp) {
        LOG("Failed to open %s", id_txt);
        free(id_txt);
        return NULL;
    }

    memset(UUID, 0, 37);
    for (int i = 0; i < 36;) {
        int c = getc(fp);
        if (c == EOF) {
            break;
        }

        // skip non UUID chars -- make the logic easier by accepting everything
        // above '-' in the ASCII table
        if (c < '-') {
            continue;
        }

        UUID[i++] = c;
    }

    fclose(fp);

    if (strcmp(UUID, BUILD_ID) == 0) {
        // Return the runtime dir with the AppRun by shortening id_txt
        const size_t slash_idx = strlen(id_txt) - 15; // 15 == strlen("/runtime-id.txt");
        id_txt[slash_idx]      = '\0';
        LOG("Found meson-runtime %s", id_txt);
    } else {
        // Wrong UUID
        printf("Found exsisting meson-runtime, but the UUID in %s does not match\n.", id_txt);
        free(id_txt);
        id_txt = NULL;
    }
    return id_txt;
}

void exec_already_extracted_runtime(const char *runtime_dir, int argc, char **argv) {
    printf("Using exsisting meson-runtime in %s\n", runtime_dir);
    unsetenv("APPIMAGE");

    char *meson_path = malloc(strlen(runtime_dir) + 16);
    sprintf(meson_path, "%s/fakebin/meson", runtime_dir);

    char **new_argv      = malloc(sizeof(char *) * (argc + 1));
    int    new_argc      = 0;
    new_argv[new_argc++] = strdup(meson_path);
    for (int i = 1; i < argc; ++i) {
        if (!appimage_starts_with("--runtime", argv[i])) {
            new_argv[new_argc++] = strdup(argv[i]);
        }
    }
    new_argv[new_argc] = NULL;

    execv(meson_path, new_argv);

    int error = errno;
    fprintf(stderr, "Failed to run %s: %s\n", meson_path, strerror(error));
    exit(EXIT_EXECERROR);
}

typedef struct mount_data {
    char * mount_dir;
    int    argc;
    char **argv;
} mount_data_t;

void mounted_cb(appimage_context_t *const context, void *data_raw) {
    mount_data_t *data = (mount_data_t *)data_raw;
    appimage_execute_apprun(context, data->mount_dir, data->argc, data->argv, "--runtime", true);
}

int main(int argc, char *argv[]) {
    appimage_context_t context;
    char *             runtime_dir = NULL;

    if (!appimage_detect_context(&context, argc, argv)) {
        return EXIT_EXECERROR;
    }

    // Parse commandline arguments
    for (int i = 1; i < argc; i++) {
        // Check if the arg is a build and has a matching meson-runtime
        if (!runtime_dir) {
            runtime_dir = check_existing_runtime(argv[i]);
        }

        if (!appimage_starts_with("--runtime", argv[i])) {
            continue;
        }

        if (CHECK_OPT("help")) {
            print_help();
            return 0;
        } else if (CHECK_OPT("version")) {
            printf("%s\n", RUNTIME_VERSION);
            return 0;
        } else if (CHECK_OPT("info")) {
            print_info(&context);
            return 0;
        } else if (CHECK_OPT("setup")) {
            if (i >= (argc - 1)) {
                fprintf(stderr, "--runtime-setup expects exactly one parameter\n");
                print_help();
                return 1;
            }

            setup_build_dir(&context, argv[++i]);
            return 0;
        } else {
            fprintf(stderr, "Unknown runtime option '%s'\n", argv[i]);
            print_help();
            return 1;
        }
    }

    // Check if the current dir has a matching meson-runtime
    if (!runtime_dir) {
        runtime_dir = check_existing_runtime(".");
    }

    // Use the first found meson-runtime
    if (runtime_dir) {
        exec_already_extracted_runtime(runtime_dir, argc, argv);
    }

    // Self-mount and execute
    char *       mount_dir = appimage_generate_mount_path(&context, NULL);
    mount_data_t cb_data;
    cb_data.mount_dir = mount_dir;
    cb_data.argc      = argc;
    cb_data.argv      = argv;

    if (!appimage_self_mount(&context, mount_dir, &mounted_cb, &cb_data)) {
        return EXIT_EXECERROR;
    }

    return 0;
}
