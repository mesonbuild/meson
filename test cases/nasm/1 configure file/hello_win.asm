; ---------------------------------------------
; Hello World for Win64 Intel x64 Assembly
;
; by fruel (https://github.com/fruel)
; 13 June 2016
; Modified by Amyspark for NASM
; 8 December 2022
; ---------------------------------------------

default rel

%include "config.asm"

extern GetStdHandle
extern WriteConsoleA
extern ExitProcess

    SECTION .rdata
msg:    db "Hello World",10     ; the string to print, 10=cr
len:    equ $-msg               ; "$" means "here"
                                ; len is a value, not an address

    SECTION .bss
bytesWritten: resd 1

SECTION .text                   ; code section
        global main             ; make label available to linker
main:
    sub rsp, 5 * 8              ; reserve shadow space

    mov rcx, -11                ; nStdHandle (STD_OUTPUT_HANDLE)
    call GetStdHandle

    mov  rcx, rax               ; hConsoleOutput
    lea  rdx, msg               ; *lpBuffer
    mov  r8, len - 1            ; nNumberOfCharsToWrite
    lea  r9, bytesWritten       ; lpNumberOfCharsWritten
    push DWORD 0h               ; lpReserved
    push DWORD 0h               ; lpReserved
    call WriteConsoleA

    mov rcx, HELLO              ; uExitCode
    call ExitProcess
