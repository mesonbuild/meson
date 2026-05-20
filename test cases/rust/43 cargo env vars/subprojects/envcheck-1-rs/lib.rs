const PKG_NAME: &str = env!("CARGO_PKG_NAME");
const PKG_VERSION: &str = env!("CARGO_PKG_VERSION");
const PKG_VERSION_MAJOR: &str = env!("CARGO_PKG_VERSION_MAJOR");
const PKG_VERSION_MINOR: &str = env!("CARGO_PKG_VERSION_MINOR");
const PKG_VERSION_PATCH: &str = env!("CARGO_PKG_VERSION_PATCH");
const CRATE_NAME: &str = env!("CARGO_CRATE_NAME");

#[no_mangle]
pub extern "C" fn check_envs() -> i32 {
    if PKG_NAME != "envcheck" { return 1; }
    if PKG_VERSION != "1.2.3" { return 2; }
    if PKG_VERSION_MAJOR != "1" { return 3; }
    if PKG_VERSION_MINOR != "2" { return 4; }
    if PKG_VERSION_PATCH != "3" { return 5; }
    if CRATE_NAME != "envcheck" { return 6; }
    0
}
