## Add a `native : 'both'`` value

This has been added to the `add_language()` function. This allows explicitly
setting the default behavior of getting a language for both the host and build
machines. The default has been changed to `'both'`, and Meson will no longer
warn about getting no value for `native` in this function as a result.

This as also been added to `add_global_args()`, `add_global_link_args()`,
`add_project_args()`, and `add_project_link_args()`. The default for these
remains the same, but `'both'` is now allowed
