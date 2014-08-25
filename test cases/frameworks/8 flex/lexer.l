%{
#include <stdlib.h>
#include "parser.tab.h"
%}

%% 
("true"|"false")    {return BOOLEAN;}
. { yyerror(); }
