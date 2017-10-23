# Wrap review guidelines

In order to get a package in the Wrap database it must be reviewed and
accepted by someone with admin rights. Here is a list of items to
check in the review. If some item is not met it does not mean that the
package is rejected. What should be done will be determined on a
case-by-case basis. Similarly meeting all these requirements does not
guarantee that the package will get accepted. Use common sense.

## Checklist

Reviewer: copy-paste this to MR discussion box and tick all boxes that apply.

    - [ ] project() has version string
    - [ ] project() has license string
    - [ ] if new project, master has tagged commit as only commit
    - [ ] if new branch, it is branched from master
    - [ ] contains a readme.txt
    - [ ] contains an upstream.wrap file
    - [ ] download link points to authoritative upstream location
    - [ ] wrap repository contains only build system files
    - [ ] merge request is pointed to correct target branch (not master)
    - [ ] wrap works
    - [ ] repo does not have useless top level directory (i.e. libfoobar-1.0.0)
