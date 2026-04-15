project('qt5 module method test', 'cpp', meson_version: '>=1.4.0')

qtmodule = import('qt5')

# because methods like .compile_ui() request the Qt dependency
# with required: true, it is not possible to skip the test when
# Qt is absent.
#
# always ending the test with an error checks at least that there
# were no internal errors.  The actual functionality of the
# methods is checked in the "4 qt" test.
testcase expect_error('.*not found.*', how: 're')
  prep = qtmodule.compile_ui(
    sources : 'ui/mainWindow.ui',
    method: get_option('method'),
    preserve_paths: true)
  error('dummy not found error')
endtestcase
