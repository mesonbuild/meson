
import std.stdio;

import glib.Util;

int main ()
{
    auto hasAbsolutePath = Util.pathIsAbsolute("/tmp");
    if (hasAbsolutePath) {
        writeln("Hello World!");
        return 0;
    }

    return false;
}
