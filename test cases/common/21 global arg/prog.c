#ifndef MYTHING
#error "Global argument not set"
#endif

#ifdef MYCPPTHING
#error "Wrong global argument set"
#endif

#ifndef MYCANDCPPTHING
#error "Global argument not set"
#endif

#ifdef GLOBAL_NATIVE
  #ifndef ARG_NATIVE
    #error "Global is native but arg_native is not set."
  #endif

  #ifdef GLOBAL_CROSS
    #error "Both global native and global cross set."
  #endif
#else
  #ifndef GLOBAL_CROSS
    #error "Neither global_cross nor glogal_native is set."
  #endif

  #ifndef ARG_CROSS
    #error "Global is cross but arg_cross is not set."
  #endif

  #ifdef ARG_NATIVE
    #error "Global is cross but arg_native is set."
  #endif
#endif

#ifdef GLOBAL_CROSS
  #ifndef ARG_CROSS
    #error "Global is cross but arg_cross is not set."
  #endif
#else
  #ifdef ARG_CROSS
    #error "Global is cross but arg_native is set."
  #endif

  #ifdef ARG_CROSS
    #error "Global is native but arg cross is set."
  #endif
#endif

int main(int argc, char **argv) {
    return 0;
}
