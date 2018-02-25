## Improve test setup selection

Test setups are now identified (also) by the project they belong to and it
is possible to select the used test setup from a specific project. E.g.
to use a test setup `some_setup` from project `some_project` for all
executed tests one can use

    meson test --setup some_project:some_setup

Should one rather want test setups to be used from the same project as
where the current test itself has been defined, one can use just

    meson test --setup some_setup

In the latter case every (sub)project must have a test setup `some_setup`
defined in it.
