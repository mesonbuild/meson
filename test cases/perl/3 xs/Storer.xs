#define PERL_NO_GET_CONTEXT
#include "EXTERN.h"
#include "perl.h"
#include "XSUB.h"

#include <storer-lib/storer.h>
#define storer_DESTROY storer_destroy
typedef Storer * Meson__Storer;

MODULE = Meson::Storer		PACKAGE = Meson::Storer		PREFIX = storer_

PROTOTYPES : DISABLE

void
storer_DESTROY(s)
	Meson::Storer	s

int
storer_get_value(s)
	Meson::Storer	s

Meson::Storer
storer_new(class)
	char *	class
  C_ARGS:


void
storer_set_value(s, v)
	Meson::Storer	s
	int	v
