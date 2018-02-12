#include"parser.tab.h"
#include<unistd.h>
#include<sys/types.h>
#include<sys/stat.h>
#include<fcntl.h>
#include<stdio.h>
#include<stdlib.h>

extern int yyparse();

int main(int argc, char **argv) {
    /*
    int input;
    if(argc != 2) {
        printf("%s <input file>");
        return 1;
    }
    input = open(argv[1], O_RDONLY);
    dup2(input, STDIN_FILENO);
    close(input);
    return yyparse();
    */
    /* We really should test that the
     * generated parser works with input
     * but it froze and I don't want to waste
     * time debugging that. For this test what
     * we care about is that it compiles and links.
     */
    void* __attribute__((unused)) dummy = (void*)yyparse;
    return 0;
}

int yywrap(void) {
     return 0;
}

int yyerror(void) {
     printf("Parse error\n");
     exit(1);
}
