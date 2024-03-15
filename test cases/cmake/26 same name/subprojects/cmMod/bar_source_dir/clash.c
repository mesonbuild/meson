// If meson links main.c against this file, the linker will complain that `clashy` is defined twice.
void clash(void);
void clashy(){}
