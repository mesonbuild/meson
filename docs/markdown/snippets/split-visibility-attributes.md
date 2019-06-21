## Splitting of Compiler.get_function_attribute('visibility')

On macOS there is no `protected` visibility, which results in the visbility
check always failing. 0.52.0 introduces two changes to improve this situation:

1. the "visibility" check no longer includes "protected"
2. a new set of "split" checks are introduced which check for a single
   attribute instead of all attributes.

These new attributes are:
* visibility:default
* visibility:hidden
* visibility:internal
* visibility:protected