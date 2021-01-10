## "Edit and continue" (/ZI) is no longer used by default for Visual Studio

Meson was adding the `/ZI` compiler argument as an argument for Visual Studio 
in debug mode. This enables the `edit-and-continue` debugging in 
Visual Studio IDE's.

Unfortunately, it is also extremely expensive and breaks certain use cases such 
as link time code generation. Edit and continue can be enabled by manually by 
adding `/ZI` to compiler arguments.

The `/ZI` argument has now been replaced by the `/Zi` argument for debug builds.

If this is an important issue for you and would like a builtin toggle option, 
please file an issue in the Meson bug tracker.