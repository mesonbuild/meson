## New pre-commit hook for meson format

Projects using [pre-commit] now can automatically format Meson files by adding
the following configuration to `.pre-commit-config.yaml`:

```yaml
hooks:
- repo: https://github.com/mesonbuild/meson.git
  rev: '1.5.0'  # Or later version, or specific commit
  - id: meson-format
    args: [--configuration, meson.format]  # If you have a meson.format at the repository root
```

[pre-commit]: https://pre-commit.com/
