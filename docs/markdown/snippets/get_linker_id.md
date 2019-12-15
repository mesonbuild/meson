## compiler.get_linker_id()

since 0.53.0, `compiler.get_linker_id()` allows retrieving a lowercase name for the linker.
Since each compiler family can typically use a variety of linkers depending on operating system,
this helps users define logic for corner cases not otherwise easily handled.