#if os(OSX)
    import Darwin
#else
    import Glibc
#endif

let fname = Process.arguments[1]
let code = "public func getGenerated() -> Int {\n    return 42\n}\n"

let f = fopen(fname, "w")

fwrite(code, 1, Int(strlen(code)), f)
print("Name: \(fname)")
fclose(f)
