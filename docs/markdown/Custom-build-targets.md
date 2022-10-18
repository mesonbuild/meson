---
short-description: Build targets for custom languages or corner-cases
...

# Custom build targets

While Meson tries to support as many languages and tools as possible,
there is no possible way for it to cover all corner cases. For these
cases it permits you to define custom build targets. Here is how one
would use it.

```meson
comp = find_program('custom_compiler')

infile = 'source_code.txt'
outfile = 'output.bin'

mytarget = custom_target('targetname',
  output : outfile,
  input : infile,
  command : [comp, '@INPUT@', '@OUTPUT@'],
  install : true,
  install_dir : 'subdir')
```

This would generate the binary `output.bin` and install it to
`${prefix}/subdir/output.bin`. Variable substitution works just like
it does for source generation.

See [Generating Sources](Generating-sources.md) for more information on this topic.

## Details on command invocation

Meson only permits you to specify one command to run. This is by
design as writing shell pipelines into build definition files leads to
code that is very hard to maintain. If your command requires multiple
steps you need to write a wrapper script that does all the necessary
work.

When doing this you need to be mindful of the following issues:

* do not assume that the command is invoked in any specific directory
* a target called `target` file `outfile` defined in subdir `subdir`
  must be written to `build_dir/subdir/foo.dat`
* if you need a subdirectory for temporary files, use
  `build_dir/subdir/target.dir`

# Generating a full subdirectory of files (since 0.64.0)

There are many cases where one needs to generate a bunch of files
where the list of outputs is unknown. The most common case is
documentation. Tools like Doxygen, Sphinx and the like typically
generate a whole directory tree full of files that you would need to
install.

For this case Meson provides the `opaque_target` command. It is more
complex than other targets and typically require the developer to
write a small wrapper script that runs the actual tool. The syntax
looks like this.

```meson
doc_target = opaque_target('docs',
    command: find_program('adaptor_script.py'),
    args: ['--some-flag'],
    install: true,
    install_dir: 'some_dir')
```

An `opaque_target` function behaves much like a `custom_target` with
the exception that it takes the command and arguments separately. This
is needed so that Meson can insert additional integration command line
arguments to the command line. When the script is executed, the
command line looks like this.

```
adaptor_script.py --stamp=<path> --dep=<path> --scrath=<dir> \
  --out=<dir> -- --some-flag
```

The first arguments are as follows:

**--stamp** is a _stamp file_. That is, the file whose existance and
    time samp specify whether the target is up to date or not. Its
    contents are ignored. When the script is run successfully it must
    update the time stamp of this file, typically by opening it for
    writing and closing it. If the script did not succeed then it must
    delete this file if it exists. If a stamp file exists after an
    unsuccessfull run, the resulting behaviour is undefined.

**--dep** specifies the dependency file. That is, it should list all
    the source files whose changes should cause the target to be
    re-run. It should be in the same syntax (a subset of Make
    dependencies) as produced by compilers like GCC and Clang. This
    file __must__ be written. If there is no dependency information
    available, then the contents should be just a single line
    consisting of the stamp file name followed by a colon. There must
    _not_ be a space between the two.

**--scratch** points to a directory that can be used for temporary
    processing. The contents of this file are persisted over
    consecutive invocations but they are cleared on every `clean`
    operation.

**--out** points to a directory where the final output files should be
    placed. They are copied as is on install (if the `install` kwarg
    is `true`). If the script is invoked multiple times it is the
    responsibility of the script to ensure that no stray files from
    the first run remain in the dir after the second run.

**--** signals the end of integration args. Additional scripts
     specified in the target follow this one. Meson may add new
     integration flags in the future, so the script must be able to
     handle any unknown arguments before this marker (typically by
     ignoring them).
