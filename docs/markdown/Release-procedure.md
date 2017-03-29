# Release procedure

**This page is WIP. The following procedure is not yet approved for use**

# Trunk

Meson operates under the principle that trunk should (in theory) be always good enough for release. That is, all code merged in trunk must pass all unit tests. Any broken code should either be fixed or reverted immediately.

People who are willing to tolerate the occasional glitch should be able to use Meson trunk for their day to day development if they so choose.

# Major releases

Major releases are currently in the form 0.X.0, where X is an increasing number. We aim to do a major release roughly once a month, though the schedule is not set in stone. Prior to the release there is a stabilisation period of roughly a week. Major changes should not be committed during this time, but instead only small scale fixes.

# Bugfix releases

Bugfix releases contain only minor fixes to major releases and are designated by incrementing the last digit of the version number. The criteria for a bug fix release is one of the following:

 - release has a major regression compared to the previous release (making existing projects unbuildable)
 - the release has a serious bug causing data loss or equivalent
 - other unforeseen major issue

In these cases a bug fix release can be made. It shall contain _only_ the fix for the issue (or issues) in question and other minor bug fixes. Only changes that have already landed in trunk will be considered for inclusion. No new functionality shall be added.

# Requesting a bug fix release

The process for requesting that a bug fix release be made goes roughly as follows:

 - file a bug about the core issue
 - file a patch fixing it if possible
 - contact the development team and request a bug fix release (IRC is the preferred contact medium)

The request should contain the following information:

 - the issue in question
 - whether it has already caused problems for real projects
 - an estimate of how many people and projects will be affected

There is no need to write a long and complicated request report. Something like the following is sufficient:

> The latest release has a regression where trying to do Foo using Bar breaks. This breaks all projects that use both, which includes at least [list of affected projects]. This causes problems for X amount of people and because of this we should do a bugfix release.
