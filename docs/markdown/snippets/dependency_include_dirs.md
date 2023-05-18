## All dependencies now separate include directory and compile args

Prior to 1.5.0, dependencies declared with `declare_dependency` would separate
-I/-isystem into separate fields, but external dependencies would combine them
as raw arguments. This meant that using `dependency.partial_dependency(includes
: true)` would not work as expected with external dependencies, and made the
implementation more complicated. As of 1.5.0 this has been changed to separate
them in all dependencies, fixing the above issues.
