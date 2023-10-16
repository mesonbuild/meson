## Overriding bindgen language setting

Even though Meson will now tell bindgen to do the right thing in most cases,
there may still be cases where Meson does not have the intended behavior,
specifically with headers with a `.h` suffix, but are C++ headers.
