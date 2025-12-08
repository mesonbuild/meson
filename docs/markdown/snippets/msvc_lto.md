## `-Db_lto` and `-Db_pgo` now supported for MSVC

`-Db_lto` is now supported for MSVC's `/LTCG`, as is `-Db_lto_mode=thin`
for `/LTCG:INCREMENTAL`. `-Db_pgo` is also supported, and should be used
alongside `-Db_lto=true`.
