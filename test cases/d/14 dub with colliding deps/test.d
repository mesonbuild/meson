module test;

import vibe.core.core;
import vibe.http.router;
import vibe.http.server;

import std.conv;
import std.stdio;

void phrase(HTTPServerRequest req, HTTPServerResponse res)
{
    const ph = req.params["phrase"];
    res.write(ph);
}

int main(string[] args)
{
    ushort port = 3501;
    if (args.length >= 2)
    {
        port = args[1].to!ushort;
    }

    auto settings = new HTTPServerSettings;
    settings.hostName = "localhost";
    settings.port = port;
    settings.accessLogToConsole = true;

    auto router = new URLRouter();
    router.get("/:phrase", &phrase);

    listenHTTP(settings, router);

    return 0;
}

// ldc2
// -of=test-vibed test-vibed.p/test.d.o -L=--allow-shlib-undefined -link-defaultlib-shared
// -L=/home/remi/.dub/packages/vibe-core-1.22.0/vibe-core/.dub/build/epoll-debug-linux.posix-x86_64-ldc_v1.28.1-2C76832BDE67E72B41171D798C85D393/libvibe_core.a
// -L=/home/remi/.dub/packages/eventcore-0.9.20/eventcore/.dub/build/epoll-debug-linux.posix-x86_64-ldc_v1.28.1-C54FF7EAA653A69765E2F48B0BFEE9F3/libeventcore.a
// -L=/home/remi/.dub/packages/taggedalgebraic-0.11.22/taggedalgebraic/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-836696E29454C7DD52D1A785F7F064E5/libtaggedalgebraic.a
// -L=/home/remi/.dub/packages/stdx-allocator-2.77.5/stdx-allocator/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-437BD83D54EA2A4D8D5FB5582D1011CB/libstdx-allocator.a
// -L=/home/remi/.dub/packages/vibe-d-0.9.4/vibe-d/http/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-BF19200C75CFF438FB297B9B88B65AE2/libvibe-d_http.a
// -L=/home/remi/.dub/packages/diet-ng-1.8.0/diet-ng/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-28AF2CD5293501FCAE75EF4C917109B8/libdiet-ng.a
// -L=/home/remi/.dub/packages/vibe-d-0.9.4/vibe-d/crypto/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-BEB4572074E44C0CAEAA07F02FEEE1B4/libvibe-d_crypto.a
// -L=/home/remi/.dub/packages/mir-linux-kernel-1.0.1/mir-linux-kernel/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-D8F864882AF6F7E4EC02F23EE7385CC4/libmir-linux-kernel.a
// -L=/home/remi/.dub/packages/vibe-d-0.9.4/vibe-d/inet/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-8293B0C5E1F628CED8D7721C10298F62/libvibe-d_inet.a
// -L=/home/remi/.dub/packages/vibe-d-0.9.4/vibe-d/data/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-F8FBD5943D452955D976BFE63D432472/libvibe-d_data.a
// -L=/home/remi/.dub/packages/vibe-d-0.9.4/vibe-d/textfilter/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-79D850D1712B7BFEF6F68B857166A8D7/libvibe-d_textfilter.a
// -L=/home/remi/.dub/packages/vibe-d-0.9.4/vibe-d/tls/.dub/build/openssl-debug-linux.posix-x86_64-ldc_v1.28.1-33BECE5E8850E608BC28B77F7ED60E42/libvibe-d_tls.a
// -L=/home/remi/.dub/packages/vibe-d-0.9.4/vibe-d/stream/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-609BEBEEE04AAB2A70F49F8E18C8F6BA/libvibe-d_stream.a
// -L=/home/remi/.dub/packages/vibe-d-0.9.4/vibe-d/utils/.dub/build/library-debug-linux.posix-x86_64-ldc_v1.28.1-E3BF7A55FE9848585D1F0A6F06FFA540/libvibe-d_utils.a
// -L=-lz -L=-lssl -L=-lcrypto