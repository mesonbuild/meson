#include<stdio.h>
#include<string.h>

#include<first.h>
#include<second.h>
#include<third.h>

int main(int argc, char **argv) {
    if(argc != 1) {
        printf("%s takes no arguments.", argv[0]);
        return 10;
    }
    if(strcmp(component_first_localized_name(), "le_first") != 0) {
        return 1;
    }
    if(strcmp(component_second_localized_name(), "le_second") != 0) {
        return 2;
    }
    if(strcmp(component_third_localized_name(), "le_third") != 0) {
        return 3;
    }
    return 0;
}
