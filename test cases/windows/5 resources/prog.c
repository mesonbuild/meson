#include<windows.h>

// deliberately don't get MY_ICON from resource.h so that depfile generation can
// be exercised in the WindowsTests.test_rc_depends_files unit test
#define MY_ICON 1

int APIENTRY
WinMain(
    HINSTANCE hInstance,
    HINSTANCE hPrevInstance,
    LPSTR lpszCmdLine,
    int nCmdShow) {
    HICON hIcon;
    hIcon = LoadIcon(GetModuleHandle(NULL), MAKEINTRESOURCE(MY_ICON));
    return hIcon ? 0 : 1;
}
