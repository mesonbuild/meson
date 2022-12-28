if gallium_drivers.contains('auto')
  if system_has_kms_drm
    # TODO: PPC, Sparc
    if ['x86', 'x86_64'].contains(host_machine.cpu_family())
      gallium_drivers = [
        'r300', 'r600', 'radeonsi', 'nouveau', 'virgl', 'svga', 'swrast',
        'iris', 'crocus', 'i915'
      ]
    elif ['arm', 'aarch64'].contains(host_machine.cpu_family())
      gallium_drivers = [
        'v3d', 'vc4', 'freedreno', 'etnaviv', 'nouveau', 'svga',
        'tegra', 'virgl', 'lima', 'panfrost', 'swrast'
      ]
    elif ['mips', 'mips64', 'riscv32', 'riscv64'].contains(host_machine.cpu_family())
      gallium_drivers = [
        'r300', 'r600', 'radeonsi', 'nouveau', 'virgl', 'swrast'
      ]
    else
      error('Unknown architecture @0@. Please pass -Dgallium-drivers to set driver options. Patches gladly accepted to fix this.'.format(
            host_machine.cpu_family()))
    endif
  elif ['darwin', 'windows', 'cygwin', 'haiku'].contains(host_machine.system())
    gallium_drivers = ['swrast']
  else
    error('Unknown OS @0@. Please pass -Dgallium-drivers to set driver options. Patches gladly accepted to fix this.'.format(
          host_machine.system()))
  endif
endif
