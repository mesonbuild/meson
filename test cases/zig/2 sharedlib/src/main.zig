const std = @import("std");

extern "hello.1" fn hello() *const [5:0]u8;

pub fn main() !void {
    std.debug.print("Hello from {}!", .{hello()});
}
