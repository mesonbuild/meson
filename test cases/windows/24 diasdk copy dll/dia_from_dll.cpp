// Loads msdiaXXX.dll from current directory using NoRegCoCreate.
// File name is set in config.h symbol MSDIA_DLL_NAME.

#include <dia2.h>
#include <diacreate.h>
#include <windows.h>
#include <stdexcept>
#include <iostream>

#include "config.h"

int main()
{
    try {

    HRESULT hr = CoInitialize(NULL);
    if (FAILED(hr))
        throw std::runtime_error("Failed to initialize COM library");

    IDiaDataSource* datasrc;
    hr = NoRegCoCreate(MSDIA_DLL_NAME, CLSID_DiaSource, __uuidof(IDiaDataSource), (void**)&datasrc);
    if (FAILED(hr))
        throw std::runtime_error("Can't open DIA DLL");

    std::cout << "DIA was successfully loaded\n";
    return 0;

    } catch (std::exception& err) {
        std::cerr << err.what() << std::endl;
        return 1;
    }
}
