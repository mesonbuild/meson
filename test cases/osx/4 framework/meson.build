# Primitive test for adding frameworks in XCode
# When opening the xcodeproj, the Folder "Frameworks" should contain two frameworks (OpenGL.framework and Foundation.framework)
# "Target Membership" of ...
# - OpenGL.framework should be only to prog@exe
# - Foundation.framework should be only to stat@sta
# "Build Phase" / "Link Binary with Libraries" for the target 
# - "prog@exe" should be only "Foundation.framework"
# - "stat@sta" should be only "OpenGL.framework"
# see "xcode-frameworks.png" for an example

project('xcode framework test', 'c', default_options : ['libdir=libtest'])

dep_libs = dependency('appleframeworks', modules : ['OpenGL'], required : false)
if not dep_libs.found()
  error('OpenGL framework not found')
endif
assert(dep_libs.type_name() == 'appleframeworks', 'type_name is wrong')

dep_main = dependency('appleframeworks', modules : ['Foundation'])

stlib = static_library('stat', 'stat.c', install : true, dependencies: dep_libs)
exe = executable('prog', 'prog.c', install : true, dependencies: dep_main)

