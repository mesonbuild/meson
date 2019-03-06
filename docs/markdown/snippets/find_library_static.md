## Add keyword `static` to find\_library

find\_library has learned the `static` keyword. They keyword must be a boolean, where `true` only
searches for static libraries and `false` only searches for dynamic/shared. Leaving the keyword unset will
keep the old behavior of first searching for dynamic and then falling back to static.
