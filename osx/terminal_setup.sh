#!/bin/sh

defaults write com.apple.Terminal 'Window Settings' -dict-add 'Stone Ridge' '{ CommandString = "/usr/local/bin/python /Users/hurley/srhome/stoneridge/srworker.py --config /Users/hurley/srhome/stoneridge.ini --log /Users/hurley/srhome/srworker.log"; ProfileCurrentVersion = "2.02"; RunCommandAsShell = 0; name = "Stone Ridge"; type = "Window Settings"; }'
defaults write com.apple.Terminal 'Default Window Settings' 'Stone Ridge'
defaults write com.apple.Terminal 'Startup Window Settings' 'Stone Ridge'
osascript -e 'tell app "System Events"
make login item at end with properties {path:"/Applications/Utilities/Terminal.app", hidden:false}
end tell'
echo "Setting auto login user (needs root privs)"
sudo defaults write /Library/Preferences/com.apple.loginwindow.plist autoLoginUser hurley
