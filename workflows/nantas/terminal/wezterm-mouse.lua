-- Merge this binding into the existing config.mouse_bindings table.
-- Do not add a mouse_reporting = true paste binding: applications need those clicks.
return {
  {
    event = { Down = { streak = 1, button = 'Right' } },
    mods = 'NONE',
    action = require('wezterm').action.PasteFrom 'Clipboard',
  },
}
