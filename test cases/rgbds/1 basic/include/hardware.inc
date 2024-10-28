;*
;* Game Boy Hardware definitions
;* https://github.com/gbdev/hardware.inc
;*
;* Based on Jones' hardware.inc
;* And based on Carsten Sorensen's ideas.
;*
;* To the extent possible under law, the authors of this work have
;* waived all copyright and related or neighboring rights to the work.
;* See https://creativecommons.org/publicdomain/zero/1.0/ for details.
;*
;* SPDX-License-Identifier: CC0-1.0
;*
;* Trimmed version for unit tests

; --
; -- BGP ($FF47)
; -- BG Palette Data (W)
; --
; -- Bit 7-6 - Intensity for %11
; -- Bit 5-4 - Intensity for %10
; -- Bit 3-2 - Intensity for %01
; -- Bit 1-0 - Intensity for %00
; --
DEF rBGP EQU $FF47


;***************************************************************************
;*
;* Header
;*
;***************************************************************************

;*
;* Nintendo scrolling logo
;* (Code won't work on a real Game Boy)
;* (if next lines are altered.)
MACRO NINTENDO_LOGO
    DB  $CE,$ED,$66,$66,$CC,$0D,$00,$0B,$03,$73,$00,$83,$00,$0C,$00,$0D
    DB  $00,$08,$11,$1F,$88,$89,$00,$0E,$DC,$CC,$6E,$E6,$DD,$DD,$D9,$99
    DB  $BB,$BB,$67,$63,$6E,$0E,$EC,$CC,$DD,$DC,$99,$9F,$BB,$B9,$33,$3E
ENDM

; $0143 Color Game Boy compatibility code
DEF CART_COMPATIBLE_DMG     EQU $00
DEF CART_COMPATIBLE_DMG_GBC EQU $80
DEF CART_COMPATIBLE_GBC     EQU $C0

; $0146 Game Boy/Super Game Boy indicator
DEF CART_INDICATOR_GB       EQU $00
DEF CART_INDICATOR_SGB      EQU $03

; $0147 Cartridge type
DEF CART_ROM                     EQU $00
DEF CART_ROM_MBC1                EQU $01
DEF CART_ROM_MBC1_RAM            EQU $02
DEF CART_ROM_MBC1_RAM_BAT        EQU $03
DEF CART_ROM_MBC2                EQU $05
DEF CART_ROM_MBC2_BAT            EQU $06
DEF CART_ROM_RAM                 EQU $08
DEF CART_ROM_RAM_BAT             EQU $09
DEF CART_ROM_MMM01               EQU $0B
DEF CART_ROM_MMM01_RAM           EQU $0C
DEF CART_ROM_MMM01_RAM_BAT       EQU $0D
DEF CART_ROM_MBC3_BAT_RTC        EQU $0F
DEF CART_ROM_MBC3_RAM_BAT_RTC    EQU $10
DEF CART_ROM_MBC3                EQU $11
DEF CART_ROM_MBC3_RAM            EQU $12
DEF CART_ROM_MBC3_RAM_BAT        EQU $13
DEF CART_ROM_MBC5                EQU $19
DEF CART_ROM_MBC5_RAM            EQU $1A
DEF CART_ROM_MBC5_RAM_BAT        EQU $1B
DEF CART_ROM_MBC5_RUMBLE         EQU $1C
DEF CART_ROM_MBC5_RAM_RUMBLE     EQU $1D
DEF CART_ROM_MBC5_RAM_BAT_RUMBLE EQU $1E
DEF CART_ROM_MBC7_RAM_BAT_GYRO   EQU $22
DEF CART_ROM_POCKET_CAMERA       EQU $FC
DEF CART_ROM_BANDAI_TAMA5        EQU $FD
DEF CART_ROM_HUDSON_HUC3         EQU $FE
DEF CART_ROM_HUDSON_HUC1         EQU $FF

; $0148 ROM size
; these are kilobytes
DEF CART_ROM_32KB   EQU $00 ; 2 banks
DEF CART_ROM_64KB   EQU $01 ; 4 banks
DEF CART_ROM_128KB  EQU $02 ; 8 banks
DEF CART_ROM_256KB  EQU $03 ; 16 banks
DEF CART_ROM_512KB  EQU $04 ; 32 banks
DEF CART_ROM_1024KB EQU $05 ; 64 banks
DEF CART_ROM_2048KB EQU $06 ; 128 banks
DEF CART_ROM_4096KB EQU $07 ; 256 banks
DEF CART_ROM_8192KB EQU $08 ; 512 banks
DEF CART_ROM_1152KB EQU $52 ; 72 banks
DEF CART_ROM_1280KB EQU $53 ; 80 banks
DEF CART_ROM_1536KB EQU $54 ; 96 banks

; $0149 SRAM size
; these are kilobytes
DEF CART_SRAM_NONE  EQU 0
DEF CART_SRAM_8KB   EQU 2 ; 1 bank
DEF CART_SRAM_32KB  EQU 3 ; 4 banks
DEF CART_SRAM_128KB EQU 4 ; 16 banks

; $014A Destination code
DEF CART_DEST_JAPANESE     EQU $00
DEF CART_DEST_NON_JAPANESE EQU $01
