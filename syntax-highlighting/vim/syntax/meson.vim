" Vim syntax file
" Language:	Meson
" Maintainer:	Nirbheek Chauhan <nirbheek.chauhan@gmail.com>
" Last Change:	2015 Feb 23
" Credits:	Zvezdan Petkovic <zpetkovic@acm.org>
"		Neil Schemenauer <nas@meson.ca>
"		Dmitry Vasiliev
"
"		This version is copied and edited from python.vim
"		It's very basic, and doesn't do many things I'd like it to
"		For instance, it should show errors for syntax that is valid in
"		Python but not in Meson.
"
" Optional highlighting can be controlled using these variables.
"
"   let meson_space_error_highlight = 1
"

" For version 5.x: Clear all syntax items.
" For version 6.x: Quit when a syntax file was already loaded.
if version < 600
  syntax clear
elseif exists("b:current_syntax")
  finish
endif

" We need nocompatible mode in order to continue lines with backslashes.
" Original setting will be restored.
let s:cpo_save = &cpo
set cpo&vim

" https://github.com/mesonbuild/meson/wiki/Syntax
syn keyword mesonConditional	elif else if endif
syn keyword mesonRepeat	foreach endforeach
syn keyword mesonOperator	and not or

syn match   mesonComment	"#.*$" contains=mesonTodo,@Spell
syn keyword mesonTodo		FIXME NOTE NOTES TODO XXX contained

" Strings can either be single quoted or triple counted across multiple lines,
" but always with a '
syn region  mesonString
      \ start="\z('\)" end="\z1" skip="\\\\\|\\\z1"
      \ contains=mesonEscape,@Spell
syn region  mesonString
      \ start="\z('''\)" end="\z1" keepend
      \ contains=mesonEscape,mesonSpaceError,@Spell

syn match   mesonEscape	"\\[abfnrtv'\\]" contained
syn match   mesonEscape	"\\\o\{1,3}" contained
syn match   mesonEscape	"\\x\x\{2}" contained
syn match   mesonEscape	"\%(\\u\x\{4}\|\\U\x\{8}\)" contained
" Meson allows case-insensitive Unicode IDs: http://www.unicode.org/charts/
syn match   mesonEscape	"\\N{\a\+\%(\s\a\+\)*}" contained
syn match   mesonEscape	"\\$"

" Meson only supports integer numbers
" https://github.com/mesonbuild/meson/wiki/Syntax#numbers
syn match   mesonNumber	"\<\d\+\>"

" booleans
syn keyword mesonConstant	false true

" Built-in functions
syn keyword mesonBuiltin	add_global_arguments add_languages benchmark
syn keyword mesonBuiltin	build_target configuration_data configure_file
syn keyword mesonBuiltin	custom_target declare_dependency dependency
syn keyword mesonBuiltin	error executable find_program find_library
syn keyword mesonBuiltin	files generator get_option get_variable
syn keyword mesonBuiltin	gettext import include_directories install_data
syn keyword mesonBuiltin	install_headers install_man install_subdir
syn keyword mesonBuiltin	is_subproject is_variable jar library message
syn keyword mesonBuiltin	project run_command run_target set_variable
syn keyword mesonBuiltin	shared_library static_library subdir subproject
syn keyword mesonBuiltin	test vcs_tag

if exists("meson_space_error_highlight")
  " trailing whitespace
  syn match   mesonSpaceError	display excludenl "\s\+$"
  " mixed tabs and spaces
  syn match   mesonSpaceError	display " \+\t"
  syn match   mesonSpaceError	display "\t\+ "
endif

if version >= 508 || !exists("did_meson_syn_inits")
  if version <= 508
    let did_meson_syn_inits = 1
    command -nargs=+ HiLink hi link <args>
  else
    command -nargs=+ HiLink hi def link <args>
  endif

  " The default highlight links.  Can be overridden later.
  HiLink mesonStatement		Statement
  HiLink mesonConditional	Conditional
  HiLink mesonRepeat		Repeat
  HiLink mesonOperator		Operator
  HiLink mesonComment		Comment
  HiLink mesonTodo		Todo
  HiLink mesonString		String
  HiLink mesonEscape		Special
  HiLink mesonNumber		Number
  HiLink mesonBuiltin		Function
  HiLink mesonConstant		Number
  if exists("meson_space_error_highlight")
    HiLink mesonSpaceError	Error
  endif

  delcommand HiLink
endif

let b:current_syntax = "meson"

let &cpo = s:cpo_save
unlet s:cpo_save

" vim:set sw=2 sts=2 ts=8 noet:
