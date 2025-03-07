## Changes to the b_sanitize option

Before 1.8 the `b_sanitize` option was a combo option, which is an enumerated
set of values. In 1.8 this was changed to a free-form array of options where
available sanitizers are not hardcoded anymore but instead verified via a
compiler check.

This solves a number of longstanding issues such as:

 - Sanitizers may be supported by a compiler, but not on a specific platform
   (OpenBSD).
 - New sanitizers are not recognized by Meson.
 - Using sanitizers in previously-unsupported combinations.

To not break backwards compatibility, calling `get_option('b_sanitize')`
continues to return the configured value as a string, with a guarantee that
`address,undefined` remains ordered.
