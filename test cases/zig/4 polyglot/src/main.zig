const std = @import("std");
const c = @cImport({
    @cInclude("polyglot/hello.c");
});

extern fn hello() *const [5:0]u8;

pub fn main() !void {
    std.debug.print("Hello from {s}!", .{hello()});
}
