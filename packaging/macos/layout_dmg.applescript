on run arguments
    set volumeName to item 1 of arguments
    set applicationName to item 2 of arguments
    set applicationItemName to applicationName & ".app"

    tell application "Finder"
        set targetDisk to disk (volumeName as text)
        tell targetDisk
            open
            delay 1

            tell container window
                set current view to icon view
                set toolbar visible to false
                set statusbar visible to false
                set bounds to {120, 120, 840, 560}
            end tell

            set viewOptions to icon view options of container window
            set arrangement of viewOptions to not arranged
            set icon size of viewOptions to 112
            set text size of viewOptions to 14
            set label position of viewOptions to bottom
            set shows item info of viewOptions to false
            set shows icon preview of viewOptions to true
            set background picture of viewOptions to file ".background:background.png"

            set position of item (applicationItemName as text) to {180, 225}
            set position of item "Applications" to {540, 225}
            set extension hidden of item (applicationItemName as text) to true

            close container window
            open
            update without registering applications
            delay 2
        end tell
    end tell
end run
