fn main() -> Result<(), ()> {
    (mylib::answer() == 42).then_some(()).ok_or(())
}
