%{
#include <stdio.h>

extern int yylex(void);
extern int yyerror(char *s);
extern FILE *yyin;
%}

%token BOOLEAN

%%
input:
  BOOLEAN { $$ = $1;}
;
