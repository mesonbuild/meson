# Embedded Python in Windows MSI packages

Meson now ships an internal version of Python in the MSI installer packages.
This means that it can run Python scripts that are part of your build
transparently. That is, if you do the following:

    myprog = find_program('myscript.py')

Then Meson will run the script with its internal Python version if necessary.
