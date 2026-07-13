#include "lexer.ll.hpp"
#include "parser.tab.hpp"

#include <stdio.h>


int main(int argc, char **argv) {
    if(argc != 2) {
        printf("%s <input file>\n", argv[0]);
        return 1;
    }

    yyFlexLexer lex{};
}
