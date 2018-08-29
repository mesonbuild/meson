#include<stdio.h>
#include<stdlib.h>
#include<png.h>
#include<string.h>
#if !defined(_MSC_VER)
#include<unistd.h>
#endif

void open_image(const char *fname) {
    png_image image;

    memset(&image, 0, (sizeof image));
    image.version = PNG_IMAGE_VERSION;

    if(png_image_begin_read_from_file(&image, fname) != 0) {
        png_bytep buffer;

        image.format = PNG_FORMAT_RGBA;
        buffer = malloc(PNG_IMAGE_SIZE(image));

        if(png_image_finish_read(&image, NULL, buffer, 0, NULL) != 0) {
            printf("Image %s read failed: %s\n", fname, image.message);
        }
//        png_free_image(&image);
        free(buffer);
    } else {
        printf("Image %s open failed: %s", fname, image.message);
    }
}


int main(int argc, char **argv) {
    return 0;
}
