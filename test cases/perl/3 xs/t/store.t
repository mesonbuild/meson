use strict;
use warnings;

use Meson::Storer;
use Test::More tests => 2;

my $storer = Meson::Storer->Test::More::new_ok;

$storer->set_value(3);

cmp_ok( $storer->get_value, '==', 3 , "got the stored value back" );
