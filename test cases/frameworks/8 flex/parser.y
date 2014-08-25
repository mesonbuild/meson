%token BOOLEAN

%%
input:
  BOOLEAN { $$ = $1;}
;
