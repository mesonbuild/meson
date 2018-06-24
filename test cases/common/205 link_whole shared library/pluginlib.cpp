
extern bool plugin_was_loaded;

struct plugin_registrator_t {
    plugin_registrator_t() {
      plugin_was_loaded = true; // this will run on library initialization, when it is loaded
    }
} reg;