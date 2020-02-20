## Consistently report file locations relative to cwd

The paths for filenames in error and warning locations are now consistently
reported relative to the current working directory (when possible), or as
absolute paths (when a relative path does not exist, e.g. a Windows path
starting with a different drive letter to the current working directory).

(The previous behaviour was to report a path relative to the source root for all
warnings and most errors, and relative to cwd for certain parser errors)
