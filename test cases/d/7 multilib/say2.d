
import std.stdio;
import std.string : format;

int sayHello2 (string str)
{
    writeln ("Hello %s from library 2.".format (str));
    return 8;
}
