from collections import defaultdict
import re

import sublime_plugin
from SublimeLinter import sublime_linter


VIEW_HAS_NOT_CHANGED = lambda: False
PASS_PREDICATE = lambda x: True

Store = {
    'errors': sublime_linter.persist.errors.copy(),
    'filter_fn': PASS_PREDICATE,
    'user_value': '',
}


super_fn = sublime_linter.update_buffer_errors


def plugin_unloaded():
    sublime_linter.update_buffer_errors = super_fn


def update_buffer_errors(bid, view_has_changed, linter, errors):
    Store['errors'][bid] = [
        error
        for error in Store['errors'][bid]
        if error['linter'] != linter.name
    ] + errors

    super_fn(
        bid,
        view_has_changed,
        linter,
        filter_errors(errors, filename_from_linter(linter)),
    )


def refilter():
    for bid, errors in Store['errors'].items():
        for linter_name, linter_errors in group_by_linter(errors).items():
            linter = next(
                linter
                for linter in sublime_linter.persist.view_linters[bid]
                if linter.name == linter_name
            )
            super_fn(
                bid,
                VIEW_HAS_NOT_CHANGED,
                linter,
                filter_errors(linter_errors, filename_from_linter(linter)),
            )


def filename_from_linter(linter):
    return linter.view.file_name() or '<untitled>'


def group_by_linter(errors):
    by_linter = defaultdict(list)
    for error in errors:
        by_linter[error['linter']].append(error)

    return by_linter


def format_error(error, filename=''):
    return '{filename}: {linter}: {error_type}: {code}: {msg}'.format(
        filename=filename, **error
    )


def filter_errors(errors, filename=''):
    filter_fn = Store['filter_fn']

    if filter_fn is PASS_PREDICATE:
        return errors

    return [
        error for error in errors if filter_fn(format_error(error, filename))
    ]


def set_filter(pattern):
    Store.update({'user_value': pattern, 'filter_fn': make_filter_fn(pattern)})
    refilter()


def make_filter_fn(pattern):
    pattern = pattern.strip()
    if not pattern:
        return PASS_PREDICATE

    fns = [_make_filter_fn(term) for term in pattern.split(' ') if term]
    return lambda x: any(f(x) for f in fns)


def _make_filter_fn(term):
    negate = term.startswith('-')
    if negate:
        term = term[1:]

    if not term:
        return PASS_PREDICATE

    fn = re.compile(term).search
    if negate:
        return lambda x: not fn(x)

    return fn


class sublime_linter_addon_filter(sublime_plugin.WindowCommand):
    def run(self, pattern=''):
        try:
            set_filter(pattern)
        except Exception as e:
            self.window.status_message("Invalid pattern: {!r}".format(e))
        else:
            if pattern:
                self.window.status_message(
                    "Filter pattern set to {!r}.".format(pattern)
                )
            else:
                self.window.status_message("Reset filter pattern.")

    def input(self, args):
        if 'pattern' in args:
            return None

        return PatternInputHandler(self.window)


class PatternInputHandler(sublime_plugin.TextInputHandler):
    def __init__(self, window):
        self.window = window

    def preview(self, pattern):
        try:
            make_filter_fn(pattern)
        except re.error as e:
            exc_str = str(e)
            return "{}{}.".format(exc_str[0].upper(), exc_str[1:])

        set_filter(pattern)

    def validate(self, pattern):
        try:
            make_filter_fn(pattern)
        except re.error:
            return False
        else:
            return True

    def initial_text(self):
        return Store['user_value']

    def cancel(self):
        self.window.run_command('sublime_linter_addon_filter', {'pattern': ''})


class sublime_linter_addon_cycle_filter_patterns(sublime_plugin.WindowCommand):
    def run(self, patterns):
        current_value = Store['user_value']
        try:
            next_index = patterns.index(current_value) + 1
        except ValueError:
            next_index = 0

        pattern = patterns[next_index % len(patterns)]
        self.window.run_command(
            'sublime_linter_addon_filter', {'pattern': pattern}
        )


sublime_linter.update_buffer_errors = update_buffer_errors
