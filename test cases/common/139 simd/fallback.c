#include<simdfuncs.h>

void increment_fallback(float arr[4]) {
    for(int i=0; i<4; i++) {
        arr[i]++;
    }
}
