extern crate foo1;
extern crate foo2;

pub fn func() -> i32 {
    foo1::foo1() + foo2::foo2()
}
