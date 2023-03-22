project('slngen', 'cpp', meson_version: '>=1.0.99', default_options: ['backend=ninja'])

if get_option('backend') != 'ninja'
    warning('This test only run with ninja backend')
    subdir_done()
endif

add_global_arguments(
    '-DGLOBAL',
    language: 'cpp'
)

add_project_arguments(
    '-DPROJECT',
    language: 'cpp'
)

exe = executable(
    'myprog', 
    'src/prog.cpp', 
    include_directories: [meson.global_source_root() / 'include'],
    cpp_args: ['-DLOCAL']
)


vs = import('unstable-visualstudio')

vsproj = vs.project(exe,
    subdir: 'myprog',
    headers: 'include/prog.h',
)

vsproj.generate(output_dir: 'vs/projects/')

sln = vs.solution('VsSolution')
sln.add_project(vsproj, subdir: 'subdir')
sln.generate(
    output_dir: 'vs/',
    project_dir: 'projects',
)


pymod = import('python')
py = pymod.find_installation('python3')

test('test generated solution', py, args: [meson.global_source_root() / 'test_generated_solution.py'])
