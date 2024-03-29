#!/bin/bash

# Check if an argument is provided
if [ $# -eq 0 ]; then
    echo "Please provide a file extension as an argument."
    exit 1
fi

fileName="$1"
fileExtension="$2"

# AppleScript command to show save dialog and enforce the file extension
saveDialog=$(osascript <<APPLESCRIPT
    set defaultName to "$fileName.$fileExtension"
    set theFile to choose file name with prompt "Please choose a location to save your file:" default name defaultName
    -- Enforce the provided file extension
    set filePath to POSIX path of theFile
    if filePath does not end with ".$fileExtension" then
        set filePath to filePath & ".$fileExtension"
    end if
    return filePath
APPLESCRIPT
)

# Check if a file path was chosen
if [ ! -z "$saveDialog" ]; then
    echo "$saveDialog"
    # Here you can add the logic to save the data to the file path chosen by the user
else
    echo "cancelled"
fi
