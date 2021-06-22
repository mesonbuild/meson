## New `vs2012` and `vs2013` backend options

Adds the ability to generate Visual Studio 2012 and 2013 projects.  This is an
extension to the existing Visual Studio 2010 projects so that it is no longer
required to manually upgrade the generated Visual Studio 2010 projects.

Generating Visual Studio 2010 projects has also been fixed since its developer
command prompt does not provide a `%VisualStudioVersion%` envvar.

## Developer environment

Expand the support for the `link_whole:` project option for pre-Visual Studio 2015
Update 2, where previously Visual Studio 2015 Update 2 or later was required for
this, for the Ninja backend as well as the vs2010 (as well as the newly-added
vs2012 and vs2013 backends).
