
import std.stdio;
import std.string : format;

int sayHello1 (string str)
{
    writeln ("Hello %s from library 1.".format (str));
    return 4;
}
