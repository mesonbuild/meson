## Add `depth` option to `wrap-git`

To allow shallow cloning, an option `depth` has been added to `wrap-git`.
This applies recursively to submodules when `clone-recursive` is set to `true`.

Note that the git server may have to be configured to support shallow cloning
not only for branches but also for tags.
