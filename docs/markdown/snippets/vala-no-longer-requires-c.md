## Using Vala no longer requires C in the project languages

Meson will now add C automatically. Since the use of C is an implementation
detail of Vala, Meson shouldn't require users to add it.
