# SPDX-License-Identifier: Apache-2.0

import unittest

from mesonbuild.mesonlib import (
    Version, version_compare, version_compare_many,
    version_compare_condition_with_min, search_version,
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
