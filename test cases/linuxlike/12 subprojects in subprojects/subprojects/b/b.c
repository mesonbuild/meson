#if defined(WITH_C)
#include "c.h"
#endif

int b_fun(){
#if defined(WITH_C)
return c_fun();
#else
return 0;
#endif
}
