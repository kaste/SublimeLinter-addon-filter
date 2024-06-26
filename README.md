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



## Theme support

The plugin will set `sl_filtered_errors` if results are filtered. You can use this to customize your theme.


## Example and mandatory gif

Using 

```
  { "keys": ["ctrl+k", "ctrl+f"],
    "command": "sublime_linter_addon_cycle_filter_patterns",
    "args": {
      "patterns": ["-annotations:", "annotations:", ""]
    }
  },
```

I switch 'annotations' on and off. 

![](https://user-images.githubusercontent.com/8558/45646940-f6192700-bac4-11e8-99f6-6b902cb8f229.gif)

Please note, that the status bar also indicates by its color that a filter is applied.
