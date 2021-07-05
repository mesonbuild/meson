## The `import()` function gains `required` and `disabler` arguments

In addition, modules now have a `found()` method, like programs and
dependencies. This allows them to be conditionally required, and used in most
places that an object with a `found()` method can be.
