
import std.stdio;
import std.string : format;

int printLibraryString (string str)
{
    writeln ("Library says: %s".format (str));
    return 4;
}
