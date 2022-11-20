## project license keyword argument as an array has been deprecated

Meson has traditionally supported using either a string or an array of strings
as the `license` argument to `project`. More recently it has been strongly
suggested to use an SPDX license expression string instead. SPDX is now an ISO
standard, and is well understood outside of Meson. When used in a Software Bill
of Materials it is natively understood by many tools. An array of licenses is
ambiguous, does `['Apache-2.0', 'GPL-2.0-only']` mean `Apache-2.0 AND GPL-2.0-only`
or `Apache-2.0 OR GPL-2.0-only`? These mean very different things, as the first
is widely believed to be incompatible, and the latter is widely understood to
mean "Apache-2.0 in general, but you may use it as GPL-2.0 for projects using
that license", as Apache-2.0 and GPL-2.0 are generally understood to be
incompatible.

Because of this ambiguity, passing an array has been deprecated and will be
removed in the future.
