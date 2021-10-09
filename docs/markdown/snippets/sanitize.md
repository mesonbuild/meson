## Improvements to the `b_sanitize` builtin option

Any valid combination of sanitizers (for example `thread,undefined`)
can be specified now.

In addition, `b_sanitize` can contain `leak` to enable LeakSanitizer.
