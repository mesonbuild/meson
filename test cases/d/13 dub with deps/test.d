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
    ushort port = 3500;
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
