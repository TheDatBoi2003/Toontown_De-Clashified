from direct.directnotify import DirectNotifyGlobal
from panda3d.core import loadPrcFileData

from otp.settings.Settings import Settings


class ToontownSettings(Settings):
    notify = DirectNotifyGlobal.directNotify.newCategory('ToontownSettings')

    def loadFromSettings(self):

        # VIDEO SETTINGS

        # Setting for toggling stretched screen.
        # Stretched screen forces the aspect ratio to be 4:3, or 1.333.
        stretchedScreen = self.getBool('game', 'stretched-screen', False)
        if stretchedScreen:
            loadPrcFileData('toonBase Settings Stretched Screen', 'aspect-ratio 1.333')
        else:
            self.updateSetting('game', 'stretched-screen', stretchedScreen)

        smoothAnimation = self.getBool('game', 'interpolate-animations', False)
        loadPrcFileData('toonbase Settings interpolate-animations', 'interpolate-animations')
        self.updateSetting('game', 'interpolate-animations', smoothAnimation)

        # Setting for a semi-custom Magic Word activator.
        # We will give players a list of which activators will work, and which will not.
        magicWordActivator = self.getInt('game', 'magic-word-activator', 0)
        loadPrcFileData('toonBase Settings Magic Word Activator', 'magic-word-activator %d' % magicWordActivator)
        self.updateSetting('game', 'magic-word-activator', magicWordActivator)

        # GAMEPLAY SETTINGS

        showCogLevels = self.getBool('game', 'show-cog-levels', True)
        loadPrcFileData('toonbase Settings show-cog-levels', 'show-cog-levels')
        self.updateSetting('game', 'show-cog-levels', showCogLevels)

        # CONTROL SETTINGS

        wantKeymaps = self.getBool('game', 'custom-keymap', False)
        loadPrcFileData('toonbase Settings Enable Custom Keybinds', 'custom-keymap')
        self.updateSetting('game', 'custom-keymap', wantKeymaps)

        jumpCancelPie = self.getBool('game', 'jump-cancels-pie', False)
        loadPrcFileData('toonbase Settings Jumping Cancels Pie Throwing', 'jump-cancels-pie')
        self.updateSetting('game', 'jump-cancels-pie', jumpCancelPie)

        keymap = self.settings.get('keymap', {'MOVE_UP': 'arrow_up', 'MOVE_DOWN': 'arrow_down',
                                              'MOVE_LEFT': 'arrow_left', 'MOVE_RIGHT': 'arrow_right',
                                              'JUMP': 'control', 'INVENTORY': 'home', 'QUESTS': 'end',
                                              'ACTION_BUTTON': 'delete', 'SECOND_ACTION_BUTTON': 'insert',
                                              'SCREENSHOT_KEY': 'f9', 'SPRINT': 'shift', 'CHAT_HOTKEY': 'enter'})
        # Fixing unicode issues
        import json
        import ast
        keymap = ast.literal_eval(json.dumps(keymap))
        loadPrcFileData('toonbase Settings keymap', 'keymap')
        if not self.settings.get('keymap'):
            self.settings['keymap'] = {}
        for bind in keymap.keys():
            self.settings['keymap'][bind] = keymap[bind]
        self.writeSettings()

        # CAMERA SETTINGS

        newCamera = self.getBool('camera', 'new-camera', False)
        loadPrcFileData('toonBase Settings Use New Camera', 'new-camera')
        self.updateSetting('camera', 'new-camera', newCamera)

        cameraSensitivity = self.getList('camera', 'camera-sensitivity', [0.1, 0.1])
        loadPrcFileData('toonBase Settings Camera Sensitivity', 'camera-sensitivity')
        self.updateSetting('camera', 'camera-sensitivity', cameraSensitivity)
