## `meson rewrite` can modify `extra_files`

The build script rewriter can now modify targets' `extra_files` lists,
or create them if absent. It it used in the same way as with rewriting
source lists:

```bash
meson rewrite target <target name/id> {add_extra_files/rm_extra_files} [list of extra files]
```

The rewriter's script mode also supports these actions:

```json
{
  "type": "target",
  "target": "<target name>",
  "operation": "extra_files_add / extra_files_rm",
  "sources": ["list", "of", "extra", "files", "to", "add, remove"],
}
```

## `meson rewrite target <target> info` outputs *target*'s `extra_files`

Targets' `extra_files` lists are now included in the rewriter's target info dump
as a list of file paths, in the same way `sources` are. This applies to both
`meson rewrite` CLI and script mode.
