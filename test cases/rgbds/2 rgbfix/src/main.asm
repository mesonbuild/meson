INCLUDE "hardware.inc"

SECTION "start",ROM0[$0100]
    nop
    jp begin

    ;; leave space for rgbfix to add the ROM header.
    ds $150 - $104

begin:
    di
    ld sp,$ffff

init:
    ld a, %11111100
    ld [rBGP], a                ; clear the screen

wait:
    halt
    nop
    jr wait
