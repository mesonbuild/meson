%include "config.asm"

global main
extern puts

section .data
  hi db 'Hello, World', 0

%ifdef FOO
%define RETVAL HELLO
%endif

section .text
main:
  push rbp
  lea rdi, [rel hi]
  call puts wrt ..plt
  pop rbp
  mov ebx,RETVAL
  mov eax,1
  int 0x80
