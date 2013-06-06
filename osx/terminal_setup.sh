#!/bin/sh

defaults write com.apple.Terminal 'Window Settings' -dict-add 'Stone Ridge' '{ CommandString = "/usr/local/bin/python /Users/stoneridge/stoneridge/srworker.py --config /Users/stoneridge/stoneridge.ini --log /Users/stoneridge/logs/srworker.log"; ProfileCurrentVersion = "2.02"; RunCommandAsShell = 0; name = "Stone Ridge"; type = "Window Settings"; }'
defaults write com.apple.Terminal 'Default Window Settings' 'Stone Ridge'
defaults write com.apple.Terminal 'Startup Window Settings' 'Stone Ridge'
