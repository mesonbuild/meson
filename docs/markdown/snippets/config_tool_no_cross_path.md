## Config tool based dependencies no longer search PATH for cross compiling

Before 0.55.0 config tool based dependencies (llvm-config, cups-config, etc),
would search system $PATH if they weren't defined in the cross file. This has
been a source of bugs and has been deprecated. It is now removed, config tool
binaries must be specified in the cross file now or the dependency will not
be found.
