#! perl
use Getopt::Long;
use ExtUtils::Install;
use File::Path 'mkpath';
use File::Copy;
use File::Basename;
use File::Spec::Functions;

my ($so, $pm);
GetOptions('so=s' => \$so, 'pm=s' => \$pm) or die("Error in command line arguments\n");
die "Have to specify -so or -pm\n" unless defined $so || defined $pm;
die "Cannot specify -so and -pm\n" if defined $so && defined $pm;

for my $file (@ARGV) {
    if ($so) {
	my ($name, $dirs, $suffix) = fileparse($file, qr/\.[^.]*/);
	my $path = catdir('blib', 'arch', 'auto', ($so || ()), $name);
	mkpath([$path]);
	copy($file, catfile($path, "$name$suffix"));
    } elsif ($pm) {
	my ($name, $dirs, $suffix) = fileparse($file, qr/\.[^.]*/);
	my $strip = catfile('', 'lib', '');
	$dirs =~ s{^.*?\Q$strip}{};
	my $path = catdir('blib', 'lib', $dirs);
	mkpath([$path]);
	pm_to_blib({$file, catfile($path, "$name$suffix")});
    }
}
