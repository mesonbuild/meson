test('load',
  perl,
  # XXX: -Is should be implicit
  args : [ '-MExtUtils::testlib', files('Meson-Storer.t') ],
  depends : [ blib_t ],
)

test('store',
  perl,
  # XXX: -Is should be implicit
  args : [ '-MExtUtils::testlib', files('store.t') ],
  depends : [ blib_t ],
)
