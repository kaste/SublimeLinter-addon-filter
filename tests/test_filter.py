import importlib
import re
import unittest


plugin = importlib.import_module('SublimeLinter-addon-filter.plugin')


class TestFilter(unittest.TestCase):
    def test_empty_pattern_uses_pass_predicate(self):
        for pattern in ('', ' ', '\t\n', '   '):
            with self.subTest(pattern=pattern):
                self.assertIs(plugin.make_filter_fn(pattern), plugin.PASS_PREDICATE)

    def test_single_positive_term(self):
        self.assertShown('F401', ['F401'])

    def test_positive_terms_are_alternatives(self):
        self.assertShown('F401 F841', ['F401', 'F841'])

    def test_single_negative_term(self):
        self.assertShown('-F401', ['F841', 'E711'])

    def test_all_negative_terms_must_pass(self):
        self.assertShown('-F401 -F841', ['E711'])

    def test_negative_terms_restrict_positive_matches(self):
        self.assertShown('F401 F841 -F401', ['F841'])
        self.assertShown('F841 -F401', ['F841'])
        self.assertShown('-F401 F841', ['F841'])

    def test_lone_minus_is_neutral(self):
        self.assertShown('-', ['F401', 'F841', 'E711'])
        self.assertShown('F841 -', ['F841'])
        self.assertShown('-F401 -', ['F841', 'E711'])

    def test_repeated_spaces_are_ignored(self):
        self.assertShown('  F401   F841  -F401  ', ['F841'])

    def test_terms_are_regular_expressions(self):
        self.assertShown(r'F\d+', ['F401', 'F841'])
        self.assertShown(r'-F\d+', ['E711'])
        self.assertShown('.*', ['F401', 'F841', 'E711'])
        self.assertShown('-.*', [])

    def test_literal_tab_is_part_of_the_regex(self):
        predicate = plugin.make_filter_fn('foo\tbar')
        self.assertTrue(predicate('foo\tbar'))
        self.assertFalse(predicate('foo'))
        self.assertFalse(predicate('bar'))

    def test_literal_tab_in_character_class(self):
        predicate = plugin.make_filter_fn('[\t]')
        self.assertTrue(predicate('foo\tbar'))
        self.assertFalse(predicate('foobar'))

    def test_invalid_regex_is_rejected(self):
        for pattern in ('[', '-[', 'F401 -['):
            with self.subTest(pattern=pattern):
                with self.assertRaises(re.error):
                    plugin.make_filter_fn(pattern)

    def assertShown(self, pattern, expected):
        predicate = plugin.make_filter_fn(pattern)
        errors = ['F401', 'F841', 'E711']
        self.assertEqual([error for error in errors if predicate(error)], expected)
