
#include "lexer.l.h"
#include "parser.tab.h"

#include <stdio.h>


int main(int argc, char **argv) {
    if(argc != 2) {
        printf("%s <input file>\n", argv[0]);
        return 1;
    }
    yyin = fopen(argv[1], "r");
    return yyparse();
}

int yywrap(void) {
     return 0;
}

int yyerror(char* s) {
     printf("Parse error: %s\n", s);
     exit(1);
}
