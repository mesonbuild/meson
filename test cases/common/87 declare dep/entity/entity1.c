#include"entity.h"

#ifdef USING_ENT
#error "Entity use flag leaked into entity compilation."
#endif

int entity_func1() {
    return 5;
}
