project('rgbds-test', 'rgbds')

rgbfix = find_program('rgbfix', required: true)

rom = executable('rgbdstest', 'src/main.asm',
                 include_directories: ['include'],
                 link_language: 'rgbds')

custom_target(output: 'rgbdstest.gb',
              input: rom,
              command: [
                rgbfix,
                '--title', 'EXAMPLE',
                '--old-licensee', '0x33',
                '--mbc-type', 'ROM',
                '--rom-version', '0',
                '--non-japanese',
                '--validate',
                '-',
              ],
              build_by_default: true,
              capture: true,
              feed: true)
