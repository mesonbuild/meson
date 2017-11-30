#include<stdlib.h>
#include<stdint.h>
#include<x264.h>

int main(int argc, char **argv) {
    x264_t *h;
    h = x264_encoder_open(NULL);
    x264_encoder_close(h);
    return 0;
}
