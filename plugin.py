from collections import defaultdict
from functools import partial
import re

import sublime
import sublime_plugin
from SublimeLinter.lint import persist


MYPY = False
if MYPY:
    from typing import Any, Callable, DefaultDict, Dict, List, Optional
    from mypy_extensions import TypedDict

    FileName = str
    LinterName = str
    Reason = str
    LintError = persist.LintError

    _State = TypedDict(
        '_State',
        {
            'errors': Dict[FileName, List[LintError]],
            'filter_fn': Callable[[str], bool],
            'user_value': str,
        },
    )


THEME_FLAG = 'sl_filtered_errors'
VIEW_HAS_NOT_CHANGED = lambda: False
PASS_PREDICATE = lambda x: True
NO_OP = lambda *a, **k: ...

Store = {
    'errors': persist.file_errors.copy(),
    'filter_fn': PASS_PREDICATE,
    'user_value': '',
}  # type: _State


def canonical_filename(view):
    # type: (sublime.View) -> str
    return view.file_name() or '<untitled {}>'.format(view.buffer_id())


class GarbargeController(sublime_plugin.EventListener):
    def on_pre_close(self, view):
        filename = canonical_filename(view)
        views_into_buffer = [
            view
            for window in sublime.windows()
            for view in window.views()
            if canonical_filename(view) == filename
        ]

        if len(views_into_buffer) <= 1:
            Store['errors'].pop(filename, None)


super_fn = NO_OP


def plugin_loaded():
    from SublimeLinter import sublime_linter

    global super_fn

    super_fn = sublime_linter.update_file_errors
    sublime_linter.update_file_errors = update_file_errors


def plugin_unloaded():
    from SublimeLinter import sublime_linter

    global super_fn

    set_filter('')

    sublime_linter.update_file_errors = super_fn
    super_fn = NO_OP


def update_file_errors(filename, linter, errors, reason=None):
    # type: (FileName, LinterName, List[LintError], Optional[Reason]) -> None
    Store['errors'][filename] = [
        error
        for error in Store['errors'][filename]
        if error['linter'] != linter
    ] + errors

    super_fn(filename, linter, filter_errors(errors), reason=reason)


def refilter() -> None:
    for filename, errors in Store['errors'].items():
        for linter_name, linter_errors in group_by_linter(errors).items():
            super_fn(filename, linter_name, filter_errors(linter_errors))


def sample_one_error(window: sublime.Window) -> "Optional[str]":
    # Samples one error for the nice help message for the TextInputHandler.
    # We take the store in `sublime_linter` bc that's the one that only holds
    # *filtered* errors. We do the sorting to *prioritize* errors from the
    # active view or at least current window.

    view = window.active_view()
    top_filename = canonical_filename(view) if view else ''
    other_filenames = {canonical_filename(view) for view in window.views()}

    def key_fn(filename_errors):
        filename, _ = filename_errors
        return (
            'a'
            if filename == top_filename
            else 'b'
            if filename in other_filenames
            else 'c'
        )

    for filename, errors in sorted(persist.file_errors.items(), key=key_fn):
        if not errors:
            continue

        error = errors[0]
        return format_error(error)
    else:
        return None


def group_by_linter(
    errors: "List[LintError]"
) -> "Dict[LinterName, List[LintError]]":
    by_linter = defaultdict(
        list
    )  # type: DefaultDict[LinterName, List[LintError]]
    for error in errors:
        by_linter[error['linter']].append(error)

    return by_linter


def format_error(error: "LintError") -> str:
    return '{filename}: {linter}: {error_type}: {code}: {msg}'.format(**error)


def filter_errors(errors: "List[LintError]") -> "List[LintError]":
    filter_fn = Store['filter_fn']

    if filter_fn is PASS_PREDICATE:
        return errors

    return [error for error in errors if filter_fn(format_error(error))]


def set_filter(pattern: str) -> None:
    Store.update({'user_value': pattern, 'filter_fn': make_filter_fn(pattern)})
    refilter()
    set_theme_flag(bool(pattern))


def make_filter_fn(pattern: str) -> "Callable[[str], bool]":
    pattern = pattern.strip()
    if not pattern:
        return PASS_PREDICATE

    fns = [_make_filter_fn(term) for term in pattern.split(' ') if term]
    return lambda x: any(f(x) for f in fns)


def _make_filter_fn(term: str) -> "Callable[[str], Any]":
    negate = term.startswith('-')
    if negate:
        term = term[1:]

    if not term:
        return PASS_PREDICATE

    fn = re.compile(term).search
    if negate:
        return lambda x: not fn(x)

    return fn


def set_theme_flag(flag: bool) -> None:
    global_settings = sublime.load_settings('Preferences.sublime-settings')
    if flag:
        global_settings.set(THEME_FLAG, True)
    else:
        global_settings.erase(THEME_FLAG)


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
            hint_msg = PATTERN_ERROR_HINT.format(
                exc_str[0].upper() + exc_str[1:]
            )
        else:
            # Work-around https://github.com/SublimeTextIssues/Core/issues/2884
            # Calling this from the worker doesn't crash at least but the UX
            # is bad. 1. It is too laggy, 2. `sample_one_error` will work on
            # wrong, outdated data set.
            sublime.set_timeout_async(partial(set_filter, pattern))

            sample_error = sample_one_error(self.window)
            hint_msg = (
                EXAMPLE_MATCH_HINT.format(
                    sample_error.replace('<', '&lt;').replace('>', '&gt;')
                )
                if sample_error
                else NO_MATCH_HINT
            )

        return sublime.Html(HELP_MESSAGE.format(hint=hint_msg))

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


HELP_MESSAGE = '''
    <style>
        span {{
            padding: 2px;
        }}
    </style>
    Search term will match against:
    <i>filename</i>:
    <i>linter</i>:
    <i>error_type</i>:
    <i>code</i>:
    <i>msg</i>
    <br /><br />
    {hint}
    <br /><br />
    Prepend '-' to negate
'''
EXAMPLE_MATCH_HINT = '''
    Example match:
    <br />
    <span style="background-color: color(black alpha(0.25));">
        {}
    </span>
'''
NO_MATCH_HINT = '''
    <span style="background-color: color(red alpha(0.25));">
        No match
    </span>
'''
PATTERN_ERROR_HINT = '''
    <span style="background-color: color(red alpha(0.25));">
        {}
    </span>
'''
