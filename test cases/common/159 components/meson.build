project('component', 'c')

libcomp = component('lib')
lib = library('simplelib', 'simplelib.c', components: libcomp)

pkgg = import('pkgconfig')
pkgg.generate(
  libraries : [lib],
  subdirs : '.',
  version : '1.0',
  name : 'simplelib',
  filebase : 'simple',
  description : 'A simple demo library.',
)

lib1comp = component('lib1')
lib1 = library('simplelib1', 'simplelib.c', components: lib1comp)
lib1_dep = declare_dependency(link_with: lib1)

tcomponent_default_option = component('hello1')
component_disable_by_default = component('hello3', default: 'disabled')
hello1 = executable('hello1', sources: 'hello.c',
  components: tcomponent_default_option,
  link_with: lib)
hello2 = executable('hello2', sources: 'hello.c',
  dependencies: lib1_dep,
  components: component('hello2'))
hello3 = executable('hello3', sources: 'hello.c',
        components: [component_disable_by_default])

test('disabled_by_default_test', hello3)

# All targets created in subdir/ will be in a new component called 'subcomponent'
subdir('subdir', components: [component('subcomponent')])

fakedep = dependency('nowaythisdepexists', required : false)
withdep1 = component('withdep1', dependencies: [fakedep])
assert(withdep1.dependencies() == [fakedep], 'component.dependencies() failed')
executable('withdep1', sources: 'hello.c',
           dependencies: fakedep,
           components: withdep1)

disabled_component = component('disabled', default: 'disabled')
fakedep2 = dependency('required_not_existing_with_disabled_component',
    components: disabled_component)
assert(not fakedep2.found(),
  'required_not_existing_with_disabled_component can not possibly exist' +
  ' and it was disabled anyway.')

n_component = component('disabled_adding_dep_component')
disabling_n_component_dep = dependency('disabling_n_component', required: false)

n_component.add_dependencies([disabling_n_component_dep])
assert(not n_component.enabled(), 'n_component should have been disabled by disabling_n_component' +
  'dependency')
