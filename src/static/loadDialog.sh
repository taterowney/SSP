#!/bin/bash

# AppleScript command to show open file dialog and return the chosen file path
chosenFile=$(osascript <<'APPLESCRIPT'
    set fileTypes to {"csv"} -- Example file types; adjust as needed
    set theFile to choose file with prompt "Please choose a file:" of type fileTypes without invisibles
    return POSIX path of theFile
APPLESCRIPT
)

# Check if a file path was chosen
if [ ! -z "$chosenFile" ]; then
    echo "$chosenFile"
    # Here you can add the logic to work with the selected file
else
    echo "cancelled"
fi
