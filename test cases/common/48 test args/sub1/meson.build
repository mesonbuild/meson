# Needs to be in a subdir so the @OUTPUT@ contains a path seperator since it is
# relative to the build root.
testfilect = custom_target('testfile',
                           input : testfile,
                           output : 'outfile.txt',
                           build_by_default : true,
                           command : [copy, '@INPUT@', '@OUTPUT@'])
