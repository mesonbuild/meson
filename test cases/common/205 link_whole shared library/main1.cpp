
// the "plugin" shared library will set this to true when it is loaded
bool plugin_was_loaded = false;

int main() {
    // we return 0 if the plugin was indeed loaded, 1 if not
    return plugin_was_loaded ? 0 : 1;
}
