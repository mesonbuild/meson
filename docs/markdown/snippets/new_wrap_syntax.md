## New wrap file syntax

The same syntax as [machine files](Machine-files.md) is now supported and
recommended for values:
- Quoted string values (e.g. `directory='libfoobar-1.0'`).
- Python-style list values (e.g. `program_names=['prog1', 'prog2']`)
- `+` and `/` operators and `[constants]` section (e.g. `source_url='http://example.com' / project_name + 'tar.gz'`)

The legacy syntax, where values were unquoted and lists were separated by comma,
is still supported for backward compatibility.
