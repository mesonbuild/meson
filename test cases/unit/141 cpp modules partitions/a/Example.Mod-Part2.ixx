export module Example.Mod : Part2;
import :Part1;

export int part2();
export inline int part1_twice() { return 2 * part1(); }
