import libone;

void main ()
{
    immutable ret = printLibraryString ("foo");
    assert (ret == 4);
}
