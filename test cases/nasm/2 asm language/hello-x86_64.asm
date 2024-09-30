%include "config.asm"

%ifdef FOO
%define RETVAL HELLO
%endif

    section .data
msg:    db "Hello World", 10
len:    equ $ - msg

    section .text
    global main
main:
    mov eax, 1        ; sys_write
    mov edi, 1        ; fd = STDOUT_FILENO
    mov rsi, msg      ; buf = msg
    mov rdx, len      ; count = len
    syscall

    mov eax, 60       ; sys_exit
    mov edi, RETVAL   ; exit code
    syscall
