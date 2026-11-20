-- A screenshot of the game now, saved in the bridge folder. Answers the path, or nil and why not:
-- "not_in_front" while another window covers the game (the copy comes off the screen), "black" from
-- exclusive fullscreen (use borderless).
-- python tools/bridge.py -f assets/bridge-scripts/shot.lua [name]
return shot((...))
