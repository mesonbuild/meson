INCLUDE "hardware.inc"

SECTION "start",ROM0[$0100]
    nop
    jp begin

    NINTENDO_LOGO

    db "EXAMPLE",0,0,0,0,0,0,0,0 ; Cart Name
    db CART_COMPATIBLE_DMG
    db 0,0                      ; Licensee code
    db CART_INDICATOR_GB
    db CART_ROM
    db CART_ROM_32KB
    db CART_SRAM_NONE
    db CART_DEST_NON_JAPANESE
    db $33                      ; Old licensee code
    db 0                        ; Mask ROM version
    db $a7                      ; Header checksum
    dw $5721                    ; Global checksum

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
