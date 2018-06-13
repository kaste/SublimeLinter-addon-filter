# Hi!


This is an addon for SublimeLinter. 

## Filter errors

This plugin provides a new command `sublime_linter_addon_filter` available via the Command Palette `SublimeLinter: Filter Errors`. It opens a text input field where you can type search terms. The views will update automatically while typing. Prepend a term with `-` to negate a term. Terms are full regex patterns, e.g. `-W\d\d` is totally valid. 

All terms are matched against the string `{filename}: {lintername}: {error_type}: {code}: {message}`. Unsaved views have the filename `<untitled>`.


## Cycle through patterns

Using this functionality, another command `sublime_linter_addon_cycle_filter_patterns` is provided which takes one argument `patterns` with the type `List[string]`. 

You can define a key binding for example to cycle through 'only warnings/only errors/all'.

    { "keys": ["ctrl+k", "ctrl+k"], 
      "command": "sublime_linter_addon_cycle_filter_patterns",
      "args": {
            "patterns": ["warnings: ", "errors: ", ""]
      } 
    },

## On/Off all errors

There is an on/off switch which toggles quickly all problems. You can reach the command using the Command Palette `SublimeLinter: On/Off`. Look at [`Default.sublime-commands`](https://github.com/kaste/SublimeLinter-addon-filter/blob/master/Default.sublime-commands) for how this is done.

