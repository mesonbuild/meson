## Bindgen will now use Meson's hueristic for what is a C++ header

Bindgen natively assumes that a file with the extension `.hpp` is a C++ header,
but that everything else is a C header. Meson has a whole list of extensions it
considers to be C++, and now will automatically look for those extensions and
set bindgen to treat those as C++
