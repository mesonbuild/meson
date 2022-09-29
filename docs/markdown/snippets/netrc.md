## Credentials from `~/.netrc` for `https` URLs

When a subproject is downloaded using an `https://` URL, credentials from
`~/.netrc` are now used. This avoids hardcoding login and password in plain
text in the URL itself.
