%{
#include <stdlib.h>
#include "parser.tab.h"

extern int yylex(void);
extern int yyerror(); 
%}

%% 
("true"|"false")    {return BOOLEAN;}
. { yyerror(); }
