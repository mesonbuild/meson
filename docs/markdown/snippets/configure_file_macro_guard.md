## [[configure_file]] now has a `macro_name` parameter.

This new paramater, `macro_name` allows C macro-style include guards to be added
to [[configure_file]]'s output when a template file is not given. This change
simplifies the creation of configure files that define macros with dynamic names
and want the C-style include guards.
