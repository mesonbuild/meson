extern "C" {
    fn ZSTD_maxCLevel() -> i64;
}

pub fn max_compression_level() -> i64 {
    unsafe {
        return ZSTD_maxCLevel();
    }
}