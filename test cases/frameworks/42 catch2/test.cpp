#include <catch2/catch_test_macros.hpp>

TEST_CASE("addition works") {
    REQUIRE(1 + 1 == 2);
}

TEST_CASE("skipped test") {
    SKIP("exercise JUnit output for skipped tests");
}
