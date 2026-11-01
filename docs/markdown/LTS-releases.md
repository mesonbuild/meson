---
title: Long Term Support Policy
---

## Does Meson provide Long Term Support (LTS) releases?

Yes. Meson provides long term bug fix support for the last release which
supports a given release of Python within reason. Some releases are so old, or
the Python that they support is so old that it is either too much work or
infeasible to continue supporting them

## What kind of support is this?

We will backport, or merge backports requests, that fix bugs in Meson itself, or
fix Continuous Integration (CI) for that branch. We will, in general, not
backport features to LTS releases, nor will we merge such an MR.

## What is the release cycle for LTS branches?

It is, in general, at the maintainers discretion to create new releases on the
LTS branches. In general we assume that it will be done when there are bug fixes
present on the branch to be released.

## Supported LTS releases

| Meson Version | Python Versions | Candidate for update |
| ------------- | --------------- | -------------------- |
| 0.56          | 3.5             | No                   |
| 0.61          | 3.6             | Yes                  |
| 1.11          | 3.7 3.8 3.9     | Yes                  |
