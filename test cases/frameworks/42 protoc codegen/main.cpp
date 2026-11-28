#include "toplevel.pb.h"

#include <iostream>
#include <string>

static bool check(const char *field, const std::string &actual, const std::string &expected)
{
    if (actual != expected)
    {
        std::cerr << field << " '" << actual << "' != '" << expected << "'" << std::endl;
        return false;
    }
    return true;
}

int main(int argc, char **argv)
{
    GOOGLE_PROTOBUF_VERIFY_VERSION;
    TopLevel msg;

    // One access per message type, so that every generated .pb.cc is linked.
    msg.mutable_nested()->set_value("nested");
    msg.mutable_configured()->set_value("configured");
    msg.mutable_imported()->set_value("imported");
    msg.mutable_imported_generated()->set_value("imported_generated");
    msg.mutable_import_dir()->set_value("import_dir");
    msg.mutable_custom()->set_value("custom");
    msg.mutable_multi_b()->set_value("multi_b");

    bool ok = true;
    ok &= check("nested", msg.nested().value(), "nested");
    ok &= check("configured", msg.configured().value(), "configured");
    ok &= check("imported", msg.imported().value(), "imported");
    ok &= check("imported_generated", msg.imported_generated().value(), "imported_generated");
    ok &= check("import_dir", msg.import_dir().value(), "import_dir");
    ok &= check("custom", msg.custom().value(), "custom");
    ok &= check("multi_b", msg.multi_b().value(), "multi_b");

    google::protobuf::ShutdownProtobufLibrary();
    return ok ? 0 : 1;
}
