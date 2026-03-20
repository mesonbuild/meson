# SPDX-License-Identifier: Apache-2.0

import unittest

from mesonbuild.mesonlib import (
    Range, Version, version_compare,
    version_compare_many, version_compare_condition_with_min,
    search_version,
)


class VersionComparisonTests(unittest.TestCase):

    def test_version_ordering(self):
        LT = -1
        EQ = 0
        #GT = 1

        # mostly from RPM tests
        tests = [
            ("1.0", "1.0", EQ),
            ("1_0", "1_0", EQ),
            ("1_0", "1.0", EQ),
            ("1.0", "2.0", LT),
            ("2.0", "2.0.0", LT),
            ("2.0", "2.0.1", LT),
            ("2.0.1", "2.0.1", EQ),
            ("2.0.1", "2.0.1a", LT),
            ("2.0.1a", "2.0.1a", EQ),
            ("2.10", "3.111", LT),
            ("2.456", "2.1000", LT),
            ("1.2rc1", "1.2.0", LT),
            ("5.5p1", "5.5p1", EQ),
            ("5.5p1", "5.5p2", LT),
            ("5.5p1", "5.5p10", LT),
            ("10xyz", "10.1xyz", LT),
            ("xyz10", "xyz10", EQ),
            ("xyz10", "xyz10.1", LT),
            ("xyz.4", "8", LT),
            ("xyz.4", "2", LT),
            ("5.5p2", "5.6p1", LT),
            ("5.6p1", "6.5p1", LT),
            ("6.0", "6.0.rc1", LT),
            ("10a2", "10b2", LT),
            ("1.0aa", "1.0aa", EQ),
            ("1.0a", "1.0aa", LT),
            ("10.0001", "10.1", EQ),
            ("10.0001", "10.0039", LT),
            ("1.05", "1.5", EQ),
            ("2a", "2.0", LT),
        ]

        for (a, b, result) in tests:
            with self.subTest(f'({a!r}, {b!r})'):
                ver_a = Version(a)
                ver_b = Version(b)

                self.assertEqual(ver_a <= ver_b, result <= 0, f'{ver_a} <= {ver_b}')
                self.assertEqual(ver_a < ver_b, result < 0, f'{ver_a} <= {ver_b}')
                self.assertEqual(ver_a > ver_b, result > 0, f'{ver_a} <= {ver_b}')
                self.assertEqual(ver_a >= ver_b, result >= 0, f'{ver_a} <= {ver_b}')

                self.assertEqual(ver_a == ver_b, result == 0, f'{ver_a} <= {ver_b}')
                self.assertEqual(ver_b == ver_a, result == 0, f'{ver_a} <= {ver_b}')
                self.assertEqual(ver_a != ver_b, result != 0, f'{ver_a} <= {ver_b}')
                self.assertEqual(ver_b != ver_a, result != 0, f'{ver_a} <= {ver_b}')

                self.assertEqual(ver_b <= ver_a, -result <= 0, f'{ver_a} <= {ver_b}')
                self.assertEqual(ver_b < ver_a, -result < 0, f'{ver_a} <= {ver_b}')
                self.assertEqual(ver_b > ver_a, -result > 0, f'{ver_a} <= {ver_b}')
                self.assertEqual(ver_b >= ver_a, -result >= 0, f'{ver_a} <= {ver_b}')

    def test_version_compare(self):
        """Test version_compare with operator prefixes."""
        self.assertTrue(version_compare('1.0', '>=1.0'))
        self.assertTrue(version_compare('1.1', '>=1.0'))
        self.assertFalse(version_compare('0.9', '>=1.0'))

        self.assertTrue(version_compare('1.0', '<=1.0'))
        self.assertTrue(version_compare('0.9', '<=1.0'))
        self.assertFalse(version_compare('1.1', '<=1.0'))

        self.assertTrue(version_compare('1.0', '>0.9'))
        self.assertFalse(version_compare('1.0', '>1.0'))

        self.assertTrue(version_compare('1.0', '<1.1'))
        self.assertFalse(version_compare('1.0', '<1.0'))

        self.assertTrue(version_compare('1.0', '==1.0'))
        self.assertFalse(version_compare('1.0', '==1.1'))

        self.assertTrue(version_compare('1.0', '!=1.1'))
        self.assertFalse(version_compare('1.0', '!=1.0'))

        # bare version and = means ==
        self.assertTrue(version_compare('1.0', '1.0'))
        self.assertFalse(version_compare('1.0', '1.1'))
        self.assertTrue(version_compare('1.0', '=1.0'))
        self.assertFalse(version_compare('1.0', '=1.1'))

    def test_version_compare_many(self):
        result, not_found, found = version_compare_many('1.5', ['>=1.0', '<2.0'])
        self.assertTrue(result)
        self.assertEqual(not_found, [])
        self.assertEqual(found, ['>=1.0', '<2.0'])

        result, not_found, found = version_compare_many('0.5', ['>=1.0', '<2.0'])
        self.assertFalse(result)
        self.assertEqual(not_found, ['>=1.0'])
        self.assertEqual(found, ['<2.0'])

        result, not_found, found = version_compare_many('2.5', ['>=1.0', '<2.0'])
        self.assertFalse(result)
        self.assertEqual(not_found, ['<2.0'])
        self.assertEqual(found, ['>=1.0'])

        # string condition is treated as single-element list
        result, not_found, found = version_compare_many('1.0', '>=1.0')
        self.assertTrue(result)
        self.assertEqual(not_found, [])
        self.assertEqual(found, ['>=1.0'])

    def test_version_compare_condition_with_min(self):
        # >= condition: minimum must be <= condition version
        self.assertTrue(version_compare_condition_with_min('>=0.46.0', '0.46.0'))
        self.assertTrue(version_compare_condition_with_min('>=0.50.0', '0.46.0'))
        self.assertFalse(version_compare_condition_with_min('>=0.40.0', '0.46.0'))

        # > condition: minimum must be <= condition version
        self.assertTrue(version_compare_condition_with_min('>0.46.0', '0.46.0'))
        self.assertTrue(version_compare_condition_with_min('>0.50.0', '0.46.0'))
        self.assertFalse(version_compare_condition_with_min('>0.45.0', '0.46.0'))

        # == condition: minimum must be <= condition version
        self.assertTrue(version_compare_condition_with_min('==0.46.0', '0.46.0'))
        self.assertTrue(version_compare_condition_with_min('==0.50.0', '0.46.0'))
        self.assertFalse(version_compare_condition_with_min('==0.40.0', '0.46.0'))

        # = or bare condition is the same as ==
        self.assertTrue(version_compare_condition_with_min('=0.46.0', '0.46.0'))
        self.assertTrue(version_compare_condition_with_min('0.46.0', '0.46.0'))
        self.assertFalse(version_compare_condition_with_min('0.40.0', '0.46.0'))

        # < and <= conditions always return False (includes versions older than minimum)
        self.assertFalse(version_compare_condition_with_min('<1.0.0', '0.46.0'))
        self.assertFalse(version_compare_condition_with_min('<=1.0.0', '0.46.0'))
        self.assertFalse(version_compare_condition_with_min('<0.30.0', '0.46.0'))
        self.assertFalse(version_compare_condition_with_min('<=0.30.0', '0.46.0'))

        # != condition always returns False
        self.assertFalse(version_compare_condition_with_min('!=0.40.0', '0.46.0'))

        # test behavior of two-component versions
        # '0.46.0' is mangled to '0.46' so that '>=0.46.0' works, but this is
        # not done by version_compare_condition_with_min
        self.assertFalse(version_compare_condition_with_min('>=0.46', '0.46.0'))
        self.assertFalse(version_compare_condition_with_min('>=0.46', '0.46.1'))
        self.assertTrue(version_compare_condition_with_min('>=0.46.0', '0.46'))
        self.assertTrue(version_compare_condition_with_min('>=0.46.1', '0.46'))

    def test_range_contains(self):
        """Test Range.__contains__."""
        # unbounded range contains everything
        r = Range()
        self.assertIn(5, r)
        self.assertIn(0, r)

        # min only, inclusive
        r = Range(min=3, min_eq=True)
        self.assertIn(3, r)
        self.assertIn(5, r)
        self.assertNotIn(2, r)

        # min only, exclusive
        r = Range(min=3, min_eq=False)
        self.assertNotIn(3, r)
        self.assertIn(4, r)
        self.assertNotIn(2, r)

        # max only, inclusive
        r = Range(max=7, max_eq=True)
        self.assertIn(7, r)
        self.assertIn(5, r)
        self.assertNotIn(8, r)

        # max only, exclusive
        r = Range(max=7, max_eq=False)
        self.assertNotIn(7, r)
        self.assertIn(6, r)
        self.assertNotIn(8, r)

        # both bounds, inclusive
        r = Range(min=3, min_eq=True, max=7, max_eq=True)
        self.assertIn(3, r)
        self.assertIn(5, r)
        self.assertIn(7, r)
        self.assertNotIn(2, r)
        self.assertNotIn(8, r)

        # both bounds, exclusive
        r = Range(min=3, min_eq=False, max=7, max_eq=False)
        self.assertNotIn(3, r)
        self.assertIn(5, r)
        self.assertNotIn(7, r)

        # empty range contains nothing
        r = Range(min=5, min_eq=False, max=5, max_eq=False)
        self.assertNotIn(5, r)

        # min == max, both inclusive -> single point, not empty
        r = Range(min=5, max=5, min_eq=True, max_eq=True)
        self.assertIn(5, r)

    def test_range_init_trivial(self):
        """Test that __post_init__ detects trivial ranges."""
        r = Range()
        self.assertFalse(r.is_empty)

        # min > max
        r = Range(min=7, max=3, min_eq=True, max_eq=True)
        self.assertTrue(r.is_empty)

        # min == max, not both inclusive -> empty
        r = Range(min=5, max=5, min_eq=True, max_eq=False)
        self.assertTrue(r.is_empty)

        r = Range(min=5, max=5, min_eq=False, max_eq=True)
        self.assertTrue(r.is_empty)

        r = Range(min=5, max=5, min_eq=False, max_eq=False)
        self.assertTrue(r.is_empty)

        # min == max, both inclusive -> single point, not empty
        r = Range(min=5, max=5, min_eq=True, max_eq=True)
        self.assertFalse(r.is_empty)

    def test_range_intersect(self):
        """Test Range.intersect."""
        # intersect two overlapping ranges
        a = Range(min=1, min_eq=True, max=10, max_eq=True)
        b = Range(min=5, min_eq=True, max=15, max_eq=True)
        r = a.intersect(b)
        self.assertIn(5, r)
        self.assertIn(10, r)
        self.assertNotIn(4, r)
        self.assertNotIn(11, r)

        # intersect does not mutate original
        self.assertIn(4, a)

        # intersect narrows unbounded range
        a = Range()
        b = Range(min=3, min_eq=True, max=7, max_eq=False)
        r = a.intersect(b)
        self.assertIn(3, r)
        self.assertIn(6, r)
        self.assertNotIn(2, r)
        self.assertNotIn(7, r)

        # intersect non-overlapping ranges produces empty
        a = Range(min=1, min_eq=True, max=3, max_eq=True)
        b = Range(min=5, min_eq=True, max=7, max_eq=True)
        r = a.intersect(b)
        self.assertTrue(r.is_empty)

        # intersect with matching boundary tightens eq
        a = Range(min=5, min_eq=True)
        b = Range(min=5, min_eq=False)
        r = a.intersect(b)
        self.assertEqual(5, r.min)
        self.assertNotIn(5, r)

        a = Range(max=5, max_eq=True)
        b = Range(max=5, max_eq=False)
        r = a.intersect(b)
        self.assertEqual(5, r.max)
        self.assertIn(4, r)

        # intersecting empty range stays empty
        a = Range(min=7, max=3, min_eq=True, max_eq=True)
        self.assertTrue(a.is_empty)
        b = Range(min=1, min_eq=True, max=10, max_eq=True)
        r = a.intersect(b)
        self.assertTrue(r.is_empty)

        b = Range()
        r = a.intersect(b)
        self.assertTrue(r.is_empty)

        a = Range()
        b = Range(min=7, max=3, min_eq=True, max_eq=True)
        r = a.intersect(b)
        self.assertTrue(r.is_empty)

    def test_range_always(self):
        """Range.always checks if inner is always true/false given outer."""
        outer = Range(min=5, min_eq=True, max=10, max_eq=True)
        unbounded = Range()
        empty = Range(min=7, max=3, min_eq=True, max_eq=True)

        # inner fully contains outer => true
        self.assertTrue(outer.always(Range(min=3, min_eq=True)))
        self.assertTrue(outer.always(Range(max=12, max_eq=True)))
        self.assertTrue(outer.always(unbounded))

        # inner same as outer => true
        self.assertTrue(outer.always(Range(min=5, min_eq=True, max=10, max_eq=True)))

        # inner doesn't overlap outer => false
        self.assertFalse(outer.always(Range(min=11, min_eq=True)))
        self.assertFalse(outer.always(Range(max=4, max_eq=True)))

        # inner partially overlaps => indeterminate
        self.assertIsNone(outer.always(Range(min=7, min_eq=True)))
        self.assertIsNone(outer.always(Range(max=8, max_eq=True)))

        # exclusive boundaries count as a partial overlap
        self.assertIsNone(outer.always(Range(min=5, min_eq=False)))
        self.assertIsNone(outer.always(Range(max=10, max_eq=False)))

        # outer is unbounded
        self.assertIsNone(unbounded.always(Range(min=5, min_eq=True)))
        self.assertTrue(unbounded.always(unbounded))
        self.assertFalse(unbounded.always(empty))

        # outer is empty => always false (intersection is empty)
        self.assertFalse(empty.always(Range(min=5, min_eq=True)))
        self.assertFalse(empty.always(unbounded))
        self.assertFalse(empty.always(empty))

    def test_range_str(self):
        """Test Range.__str__."""
        self.assertEqual(str(Range()), '(any)')
        self.assertEqual(str(Range(min=3, min_eq=True)), '>= 3')
        self.assertEqual(str(Range(min=3, min_eq=False)), '> 3')
        self.assertEqual(str(Range(max=7, max_eq=True)), '<= 7')
        self.assertEqual(str(Range(max=7, max_eq=False)), '< 7')
        self.assertEqual(str(Range(min=3, min_eq=True, max=7, max_eq=False)), '>= 3, < 7')
        self.assertEqual(str(Range(min=5, max=5, min_eq=True, max_eq=True)), '== 5')
        # empty range
        r = Range(min=7, max=3, min_eq=True, max_eq=True)
        self.assertEqual(str(r), '(empty)')

    def test_range_str_version(self):
        """Test Range.__str__ with Version objects."""
        r = Range(min=Version('0.46.0'), min_eq=True)
        self.assertEqual(str(r), '>= 0.46.0')
        r = Range(min=Version('1.0'), min_eq=True, max=Version('2.0'), max_eq=False)
        self.assertEqual(str(r), '>= 1.0, < 2.0')

    def test_search_version(self):
        self.assertEqual(search_version('foo 1.2.3'), '1.2.3')
        self.assertEqual(search_version('1.2.3'), '1.2.3')
        self.assertEqual(search_version('foo 2026.03.20 1.2.3'), '1.2.3')
        self.assertEqual(search_version('2026.03.20 1.2.3'), '1.2.3')
        self.assertEqual(search_version('foo 2026.03.20'), '2026.03.20')
        self.assertEqual(search_version('2026.03.20'), '2026.03.20')
        self.assertEqual(search_version('2026.03'), '2026.03')
        self.assertEqual(search_version('2026.03 1.2.3'), '1.2.3')
        self.assertEqual(search_version('foo v1.2.3'), '1.2.3')
        self.assertEqual(search_version('2026'), 'unknown version')
