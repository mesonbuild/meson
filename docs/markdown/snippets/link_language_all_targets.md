## link_language argument added to all targets

Previously the `link_language` argument was only supposed to be allowed in
executables, because the linker used needs to be the linker for the language
that implements the main function. Unfortunately it didn't work in that case,
and, even worse, if it had been implemented properly it would have worked for
*all* targets. In 0.55.0 this restriction has been removed, and the bug fixed.
It now is valid for `executable` and all derivative of `library`.
