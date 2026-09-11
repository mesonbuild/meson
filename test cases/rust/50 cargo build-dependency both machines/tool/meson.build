tool_pkg = cargo.package('tool', native: true)
tool_exe = tool_pkg.executable()

# Nothing consumes the output: what is under test is that a build-machine
# binary coming from [build-dependencies] can be run at build time at all.
custom_target('generated.rs',
  build_by_default: true,
  output: 'generated.rs',
  command: [tool_exe, '@OUTPUT@'],
)

if meson.is_cross_build()
  # "tool" is reachable only as a build-dependency, so it has no host
  # configuration at all.
  testcase expect_error('package tool-0.1.0 not configured for host machine')
    cargo.package('tool')
  endtestcase
endif
