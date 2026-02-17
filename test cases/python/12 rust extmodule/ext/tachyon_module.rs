#![allow(improper_ctypes)]

#[repr(C)]
pub struct PyModuleDef;
#[repr(C)]
pub struct PyObject;

extern "C" {
    pub static mut tachyonmodule: *mut PyModuleDef;
    pub fn PyModule_Create2(def: *mut PyModuleDef, abiver: i32) -> *mut PyObject;
}

#[allow(non_snake_case)]
#[no_mangle]
pub unsafe extern "C" fn PyInit_tachyon() -> *mut PyObject {
    PyModule_Create2(tachyonmodule, 3)
}
