extern "C" {
    fn CFAbsoluteTimeGetCurrent() -> f64;
}

pub fn get_absolute_time() -> f64 {
    unsafe { CFAbsoluteTimeGetCurrent() }
}
