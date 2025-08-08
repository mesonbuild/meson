-
short-description: SELinux policy package module
authors:
    - name: Marc-André Lureau
      email: marcandre.lureau@redhat.com
      years: [2025]
...

# Unstable SELinux Module

Meson provides a module to simplify the compilation of SELinux security
policies. It automates the process of finding the necessary tools, preprocessing
policy files, and building the final policy package.

## Finding the module

The module is named `selinux` and can be brought into your `meson.build` file
with `import()`:

```meson
selinux = import('selinux')
```
*Added 1.9.0* FIXME

## Functions

### `found()`

```meson
bool selinux.found()
```

Check if the required SELinux development tools (`m4`, `checkmodule`,
`semodule_package`) are present on the system

**Returns**:
    `true` if the required tools are found, `false` otherwise.

### `package()`

```meson
custom_tgt selinux.package(package_name: string,
                           te_file: string,
                           [if_file: string | file = None],
                           [fc_file: string | file = None],
                           [install: bool = true],
                           [install_dir: string = '/usr/share/selinux/packages'],
                           [name: string | None = None]
                           [mls: bool = true],
                           [type: string | None = None],
                           [distro: string | None = None],
                           [direct_initrc: bool | None = None])
```

This is the main function of the module. It takes all your policy source files,
compiles them, and creates a single `.pp` file, which can then be installed on
the system.

Example:
```meson
selinux.package('mydaemon', te_file: file('mydaemon.te'))
```

Only the type enforcement `.te` file is required.

### Arguments for `selinux.package`

The function has one positional argument and several keyword arguments.

#### Positional Argument

- `package_name` (string): The name of the policy package to build.

#### Keyword Arguments

| Name            | Type            | Default Value                      | Description                                                                                                     |
|-----------------|-----------------|------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| `te_file`       | `str` or `file` | `'{package_name}.te'`              | The main Type Enforcement file for the policy. Required.                                                        |
| `if_file`       | `str` or `file` | `'{package_name}.if'`              | The interface file for the policy, if any.                                                                      |
| `fc_file`       | `str` or `file` | `'{package_name}.fc'`              | The file contexts file, if any.                                                                                 |
| `install`       | `bool`          | `true`                             | If `true`, the generated `.pp` file will be installed.                                                          |
| `install_dir`   | `str`           | `<prefix>/<datadir>/selinux/policy/packages` | The directory to install the policy package to. Defaults to the system's standard location.           |
| `name`          | `str`           | Depends on /etc/selinux/config     | The name of the policy type to build for (e.g., `targeted`, `mls`).                                             |
| `type`          | `str`           | Depends on build.conf `*`          | The policy type, can be `standard`, `mls`, or `mcs`. Can be set explicitly to override auto-detection.          |
| `mls`           | `bool`          | Depends on build.conf `*`          | If `true`, enables MLS (Multi-Level Security) support in the M4 preprocessor macros.                            |
| `distro`        | `str`           | Depends on build.conf `*`          | If set, enables distro-specific M4 macros (e.g., `distro_rhel`).                                                |
| `direct_initrc` | `bool`          | Depends on build.conf `*`          | If `true`, enables the `direct_sysadm_daemon` M4 macro.                                                         |

`*` Depends on build.conf: various settings are read from the system `/usr/share/selinux/devel/include/build.conf`


**Returns**: a [[@custom_tgt]] for the `.pp` file.
