project('string formatting', 'c')

templ = '@0@bar@1@'

if templ.format('foo', 'baz') != 'foobarbaz'
  error('Basic string formatting is broken.')
endif

if '@0@'.format(1) != '1'
  error('String number formatting is broken.')
endif

if '@0@'.format(true) != 'true'
  error('String boolean formatting is broken.')
endif

templ2 = '@0@'
subs2 = '42'

if templ2.format(subs2) != '42'
  error('String formatting with variables is broken.')
endif

if 'foobarfoobar'.tr('r', 'z') != 'foobazfoobaz'
  error('String translate is broken')
endif
if 'stringtranslate'.tr('abcde', 'fghij') != 'stringtrfnslftj'
  error('String translate is broken')
endif

trtempl = 'foobarbarfoo'
if trtempl.tr('ro', 'ab') != 'fbbbaabaafbb'
  error('String translate with variables is broken')
endif
