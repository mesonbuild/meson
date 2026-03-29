use std::process::ExitCode;
fn main() -> ExitCode {
    if mylib::world() == 42 { ExitCode::SUCCESS } else { ExitCode::FAILURE }
}
