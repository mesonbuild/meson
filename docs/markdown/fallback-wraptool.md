---
title: fallback wraptool
...

# In case of emergency

In case wraptool is down we have created a backup script that you can use to download wraps directly from the GitHub repos. It is not as slick and may have bugs but at least it will allow you to use wraps.

## Using it

Currently the emergency tool is only in Meson trunk so you need a git checkout to use it. It also does not on releases older than 0.32.0 because they had a bug. (A workaround for older versions is to delete existing `foobar.wrap` files if you have them.)

To list all available wraps:

    ghwt.py list

To install a wrap, go to your source root, make sure that the `subprojects` directory exists and run this command:

    ghwt.py install <projectname>

This will stage the subproject ready to use. If you have multiple subprojects you need to download them all manually.

## How to upgrade an existing dir/fix broken state/any other problem

Nuke the contents of `subprojects` and start again.

## Known issues

Some repositories show up in the list but are not installable. They would not show up in the real WrapDB because they are works in progress.

GitHub web API limits the amount of queries you can do to 60/hour. If you exceed that you need to wait for the timer to reset.
