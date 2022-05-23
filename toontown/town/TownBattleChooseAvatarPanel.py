from toontown.toonbase.ToontownBattleGlobals import *
from toontown.toonbase import ToontownGlobals
from direct.fsm import StateData
from direct.directnotify import DirectNotifyGlobal
from toontown.battle import BattleBase, SuitBattleGlobals
from direct.gui.DirectGui import *
from panda3d.core import *
from toontown.toonbase import TTLocalizer

class TownBattleChooseAvatarPanel(StateData.StateData):
    notify = DirectNotifyGlobal.directNotify.newCategory('ChooseAvatarPanel')

    def __init__(self, doneEvent, toon):
        self.notify.debug('Init choose panel...')
        StateData.StateData.__init__(self, doneEvent)
        self.numAvatars = 0
        self.chosenAvatar = 0
        self.toon = toon

    def load(self):
        gui = loader.loadModel('phase_3.5/models/gui/battle_gui')
        self.frame = DirectFrame(relief=None, image=gui.find('**/BtlPick_TAB'), image_color=Vec4(1, 0.2, 0.2, 1))
        self.frame.hide()
        self.statusFrame = DirectFrame(parent=self.frame, relief=None, image=gui.find('**/ToonBtl_Status_BG'), image_color=Vec4(0.5, 0.9, 0.5, 1), pos=(0.611, 0, 0))
        self.textFrame = DirectFrame(parent=self.frame, relief=None, image=None, image_color=Vec4(1, 1, 0, 1), text='', text_fg=Vec4(0, 0, 0, 1), text_pos=(0, -0.025, 0), text_scale=0.08, pos=(-0.013, 0, 0.013))
        if self.toon:
            self.textFrame['text'] = TTLocalizer.TownBattleChooseAvatarToonTitle
        else:
            self.textFrame['text'] = TTLocalizer.TownBattleChooseAvatarCogTitle
        self.avatarButtons = []
        for i in xrange(SuitBattleGlobals.MAX_SUIT_CAPACITY):
            button = DirectButton(parent=self.frame, relief=None, image=(
                gui.find('**/PckMn_Arrow_Up'), gui.find('**/PckMn_Arrow_Dn'), gui.find('**/PckMn_Arrow_Rlvr')),
                                  command=self.__handleAvatar, extraArgs=[i])
            if self.toon:
                button.setScale(1, 1, -1)
                button.setPos(0, 0, -0.2)
            else:
                button.setScale(1, 1, 1)
                button.setPos(0, 0, 0.2)
            self.avatarButtons.append(button)

        self.backButton = DirectButton(parent=self.frame, relief=None, image=(gui.find('**/PckMn_BackBtn'), gui.find('**/PckMn_BackBtn_Dn'), gui.find('**/PckMn_BackBtn_Rlvr')), pos=(-0.647, 0, 0.006), scale=1.05, text=TTLocalizer.TownBattleChooseAvatarBack, text_scale=0.05, text_pos=(0.01, -0.012), text_fg=Vec4(0, 0, 0.8, 1), command=self.__handleBack)
        gui.removeNode()
        return

    def unload(self):
        self.frame.destroy()
        del self.frame
        del self.statusFrame
        del self.textFrame
        del self.avatarButtons
        del self.backButton

    def enter(self, numAvatars, localNum = None, luredIndices = None, trappedIndices = None, track = None):
        self.frame.show()
        invalidTargets = []
        if not self.toon:
            if len(luredIndices) > 0:
                if track == BattleBase.TRAP or track == BattleBase.LURE:
                    invalidTargets += luredIndices
            if len(trappedIndices) > 0:
                if track == BattleBase.TRAP:
                    invalidTargets += trappedIndices
        self.__placeButtons(numAvatars, invalidTargets, localNum)

    def exit(self):
        self.frame.hide()

    def __handleBack(self):
        doneStatus = {'mode': 'Back'}
        messenger.send(self.doneEvent, [doneStatus])

    def __handleAvatar(self, avatar):
        doneStatus = {'mode': 'Avatar',
         'avatar': avatar}
        messenger.send(self.doneEvent, [doneStatus])

    def adjustCogs(self, numAvatars, luredIndices, trappedIndices, track):
        invalidTargets = []
        if len(luredIndices) > 0:
            if track == BattleBase.TRAP or track == BattleBase.LURE:
                invalidTargets += luredIndices
        if len(trappedIndices) > 0:
            if track == BattleBase.TRAP:
                invalidTargets += trappedIndices
        self.__placeButtons(numAvatars, invalidTargets, None)
        return

    def adjustToons(self, numToons, localNum):
        self.__placeButtons(numToons, [], localNum)

    def __placeButtons(self, numAvatars, invalidTargets, localNum):
        for i in xrange(SuitBattleGlobals.MAX_SUIT_CAPACITY):
            if numAvatars > i != localNum and i not in invalidTargets:
                self.avatarButtons[i].show()
            else:
                self.avatarButtons[i].hide()

        origin = 0.0 + ((numAvatars - 1) * 0.2)
        for i in xrange(numAvatars):
            self.avatarButtons[i].setX(origin - (i * 0.4))
        return None
