// Loads DIA SDK from system registry using CoCreateInstance().
// The corresponding msdiaXXX.dll must be registered in system registry
//   (eg. run `regsvr32.exe msdia140.dll` as administrator)

#include <dia2.h>
#include <windows.h>
#include <stdexcept>
#include <iostream>

int main()
{
    try {

    HRESULT hr = CoInitialize(NULL);
    if (FAILED(hr))
        throw std::runtime_error("Failed to initialize COM library");

    IDiaDataSource* datasrc;
    hr = CoCreateInstance( CLSID_DiaSource, NULL, CLSCTX_INPROC_SERVER, __uuidof(IDiaDataSource), (void **)&datasrc);
    if (FAILED(hr))
        throw std::runtime_error("Can't create IDiaDataSource. You must register msdia*.dll with regsvr32.exe.");

    std::cout << "DIA was successfully loaded\n";
    return 0;

    } catch (std::exception& err) {
        std::cerr << err.what() << std::endl;
        return 1;
    }
}
