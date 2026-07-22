# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The Meson Development Team

load("@rules_cc//cc:defs.bzl", "CcInfo", "cc_common")

# This is the custom set of native Starlark rules used by the convert tool.
#
# Why meson_cc_flags?
#    - The normal cc_library does not propagate copts ('-Werror'), but does
#      propagate defines ('-DFOO`).  meson's notion that both are strings to
#      the compiler is a simpler and accurate model, so this codifies it.
# Why meson_cc_library?
#    - So we can use meson_cc_flags.
# Why meson_cc_headers?
#    - Meson's include_directories function is relative to current directory.
#      cc_library's is relative to the MODULE.bazel workspace root.  We need
#      to do the remapping here.
# Why meson_genrule?
#    - The normal genrule does not export_include_directories in the sandbox
#      in which it was run.  So it's impossible to #include generated_header in
#      non-root directory locations.

MesonFlagInfo = provider(fields = {
    "defines": "depset of compiler defines (-D)",
    "copts": "depset of compiler options",
    "linkopts": "depset of linker options",
})

def _add_bin_dir(ctx, path):
    """Adds the bazel-out (bin_dir) counterpart to a workspace-relative path."""
    return [path, ctx.bin_dir.path + "/" + path]

def _package_relative_includes(ctx, includes):
    """Processes includes relative to the current package's BUILD file."""
    package_path = ctx.label.package
    rebased = []
    for i in includes:
        if i == ".":
            path = package_path if package_path else "."
        else:
            path = package_path + "/" + i if package_path else i

        rebased.extend(_add_bin_dir(ctx, path))
    return rebased

def _workspace_relative_includes(ctx, includes):
    """Processes includes relative to the workspace root."""
    rebased = []
    for path in includes:
        path = path if path else "."
        rebased.extend(_add_bin_dir(ctx, path))
    return rebased

def _meson_cc_flags_impl(ctx):
    defines, copts, linkopts = [], [], []
    for f in ctx.attr.flags:
        if f.startswith("-D"):
            defines.append(f[2:])
        elif f.startswith("-l") or f.startswith("-L") or f.startswith("-Wl,"):
            linkopts.append(f)
        else:
            copts.append(f)

    # Combine with attributes and transitive dependencies
    return [
        MesonFlagInfo(
            defines = depset(
                defines,
                transitive = [
                    d[MesonFlagInfo].defines for d in ctx.attr.deps if MesonFlagInfo in d
                ],
            ),
            copts = depset(
                copts,
                transitive = [
                    d[MesonFlagInfo].copts for d in ctx.attr.deps if MesonFlagInfo in d
                ],
            ),
            linkopts = depset(
                linkopts + ctx.attr.linkopts,
                transitive = [
                    d[MesonFlagInfo].linkopts for d in ctx.attr.deps if MesonFlagInfo in d
                ],
            ),
        ),
    ]

meson_cc_flags = rule(
    implementation = _meson_cc_flags_impl,
    attrs = {
        "flags": attr.string_list(),
        "linkopts": attr.string_list(),
        "deps": attr.label_list(),
    },
)

def _meson_cc_library_impl(ctx):
    cc_toolchain = ctx.attr._cc_toolchain[cc_common.CcToolchainInfo]
    feature_config = cc_common.configure_features(ctx = ctx, cc_toolchain = cc_toolchain)

    # Collect flags from MesonFlagInfo dependencies.
    all_defines = depset(
        transitive = [
            d[MesonFlagInfo].defines for d in ctx.attr.deps if MesonFlagInfo in d
        ],
    )
    all_copts = depset(
        transitive = [
            d[MesonFlagInfo].copts for d in ctx.attr.deps if MesonFlagInfo in d
        ],
    )
    all_linkopts = depset(
        transitive = [
            d[MesonFlagInfo].linkopts for d in ctx.attr.deps if MesonFlagInfo in d
        ],
    )

    # Meson always adds current directory to include path
    rebased_includes = _package_relative_includes(ctx, ["."])

    compilation_contexts = [d[CcInfo].compilation_context for d in ctx.attr.deps if CcInfo in d]
    local_compilation_context = cc_common.create_compilation_context(defines = all_defines)

    (comp_context, comp_outputs) = cc_common.compile(
        name = ctx.label.name,
        actions = ctx.actions,
        cc_toolchain = cc_toolchain,
        feature_configuration = feature_config,
        srcs = ctx.files.srcs,
        system_includes = rebased_includes,
        user_compile_flags = all_copts.to_list(),
        compilation_contexts = [local_compilation_context] + compilation_contexts,
    )

    # Link
    linking_contexts = [d[CcInfo].linking_context for d in ctx.attr.deps if CcInfo in d]

    # Add linkopts from MesonFlagInfo
    local_linker_input = None
    if all_linkopts:
        local_linker_input = cc_common.create_linker_input(
            owner = ctx.label,
            user_link_flags = all_linkopts,
        )
    local_linking_context = cc_common.create_linking_context(
        linker_inputs = depset([local_linker_input]) if local_linker_input else depset(),
    )

    linking_outputs = cc_common.link(
        name = ctx.label.name,
        actions = ctx.actions,
        cc_toolchain = cc_toolchain,
        feature_configuration = feature_config,
        compilation_outputs = comp_outputs,
        linking_contexts = [local_linking_context] + linking_contexts,
        output_type = "dynamic_library",
    )

    linker_input = None
    if linking_outputs.library_to_link:
        linker_input = cc_common.create_linker_input(
            owner = ctx.label,
            libraries = depset([linking_outputs.library_to_link]),
        )

    linking_context = cc_common.create_linking_context(
        linker_inputs = depset([linker_input]) if linker_input else depset(),
    )

    if linking_contexts:
        linking_context = cc_common.merge_linking_contexts(
            linking_contexts = [linking_context] + linking_contexts,
        )

    outputs = []
    if linking_outputs.library_to_link:
        if linking_outputs.library_to_link.static_library:
            outputs.append(linking_outputs.library_to_link.static_library)
        elif linking_outputs.library_to_link.dynamic_library:
            outputs.append(linking_outputs.library_to_link.dynamic_library)

    return [
        DefaultInfo(files = depset(outputs)),
        CcInfo(
            compilation_context = comp_context,
            linking_context = linking_context,
        ),
        MesonFlagInfo(defines = all_defines, copts = all_copts, linkopts = all_linkopts),
    ]

meson_cc_library = rule(
    implementation = _meson_cc_library_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = True),
        "deps": attr.label_list(),
        "_cc_toolchain": attr.label(default = "@bazel_tools//tools/cpp:current_cc_toolchain"),
    },
    fragments = ["cpp"],
    toolchains = ["@bazel_tools//tools/cpp:toolchain_type"],
)

def _meson_cc_headers_impl(ctx):
    # Collect transitive compilation contexts from dependencies (likely other headers)
    compilation_contexts = [d[CcInfo].compilation_context for d in ctx.attr.deps if CcInfo in d]

    return [
        DefaultInfo(files = depset(ctx.files.hdrs)),
        CcInfo(
            compilation_context = cc_common.merge_compilation_contexts(
                compilation_contexts = [
                    cc_common.create_compilation_context(
                        headers = depset(ctx.files.hdrs),
                        system_includes = depset(
                            _package_relative_includes(ctx, ctx.attr.export_include_dirs),
                        ),
                    ),
                ] + compilation_contexts,
            ),
        ),
    ]

meson_cc_headers = rule(
    implementation = _meson_cc_headers_impl,
    attrs = {
        "hdrs": attr.label_list(allow_files = True),
        "export_include_dirs": attr.string_list(),
        "deps": attr.label_list(),
    },
)

def _meson_genrule_impl(ctx):
    command = ctx.expand_location(ctx.attr.cmd, targets = ctx.attr.srcs + ctx.attr.tools)
    ruledir = ctx.bin_dir.path + "/" + ctx.label.package
    command = command.replace("$(genDir)", ruledir).replace("$(GENDIR)", ruledir)

    ctx.actions.run_shell(
        inputs = ctx.files.srcs,
        tools = [t.files_to_run for t in ctx.attr.tools],
        outputs = ctx.outputs.outs,
        command = command,
        mnemonic = "MesonGenrule",
        progress_message = "Generating %s" % ctx.label.name,
    )

    return [
        DefaultInfo(files = depset(ctx.outputs.outs)),
        CcInfo(
            compilation_context = cc_common.create_compilation_context(
                system_includes = depset(
                    _workspace_relative_includes(ctx, ctx.attr.export_include_dirs),
                ),
                headers = depset(ctx.outputs.outs),
            ),
        ),
    ]

meson_genrule = rule(
    implementation = _meson_genrule_impl,
    attrs = {
        "srcs": attr.label_list(allow_files = True),
        "outs": attr.output_list(mandatory = True),
        "tools": attr.label_list(allow_files = True, cfg = "exec"),
        "cmd": attr.string(mandatory = True),
        "export_include_dirs": attr.string_list(),
    },
)
