extern "C" { fn hello() -> u32; }
pub fn world() -> u32 { unsafe { hello() } }
