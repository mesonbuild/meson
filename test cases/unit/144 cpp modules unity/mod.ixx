export module Example.Unity;

// Attached to the global module, so it can be used without importing.
extern "C" int mod_value() { return 1; }
