from toontown.toonbase.ToontownBattleGlobals import *
from toontown.toonbase import ToontownGlobals
from direct.fsm import StateData
from direct.directnotify import DirectNotifyGlobal
from toontown.battle import BattleBase, SuitBattleGlobals
from direct.gui.DirectGui import *
from panda3d.core import *
from toontown.toonbase import TTLocalizer

class FireCogPanel(StateData.StateData):
    notify = DirectNotifyGlobal.directNotify.newCategory('ChooseAvatarPanel')

    def __init__(self, doneEvent):
        self.notify.debug('Init choose panel...')
        StateData.StateData.__init__(self, doneEvent)
        self.numAvatars = 0
        self.chosenAvatar = 0
        self.toon = 0
        self.loaded = 0

    def load(self):
        gui = loader.loadModel('phase_3.5/models/gui/battle_gui')
        self.frame = DirectFrame(relief=None, image=gui.find('**/BtlPick_TAB'), image_color=Vec4(1, 0.2, 0.2, 1))
        self.frame.hide()
        self.statusFrame = DirectFrame(parent=self.frame, relief=None, image=gui.find('**/ToonBtl_Status_BG'), image_color=Vec4(0.5, 0.9, 0.5, 1), pos=(0.611, 0, 0))
        self.textFrame = DirectFrame(parent=self.frame, relief=None, image=gui.find('**/PckMn_Select_Tab'), image_color=Vec4(1, 1, 0, 1), image_scale=(1.0, 1.0, 2.0), text='', text_fg=Vec4(0, 0, 0, 1), text_pos=(0, 0.02, 0), text_scale=TTLocalizer.FCPtextFrame, pos=(-0.013, 0, 0.013))
        self.textFrame['text'] = TTLocalizer.FireCogTitle % localAvatar.getPinkSlips()
        self.avatarButtons = []
        for i in xrange(SuitBattleGlobals.MAX_SUIT_CAPACITY):
            button = DirectButton(parent=self.frame, relief=None, text='', text_fg=Vec4(0, 0, 0, 1), text_scale=0.067, text_pos=(0, -0.015, 0), textMayChange=1, image_scale=(1.0, 1.0, 1.0), image=(gui.find('**/PckMn_Arrow_Up'), gui.find('**/PckMn_Arrow_Dn'), gui.find('**/PckMn_Arrow_Rlvr')), command=self.__handleAvatar, extraArgs=[i])
            button.setScale(1, 1, 1)
            button.setPos(0, 0, 0.2)
            self.avatarButtons.append(button)

        self.backButton = DirectButton(parent=self.frame, relief=None, image=(gui.find('**/PckMn_BackBtn'), gui.find('**/PckMn_BackBtn_Dn'), gui.find('**/PckMn_BackBtn_Rlvr')), pos=(-0.647, 0, 0.006), scale=1.05, text=TTLocalizer.TownBattleChooseAvatarBack, text_scale=0.05, text_pos=(0.01, -0.012), text_fg=Vec4(0, 0, 0.8, 1), command=self.__handleBack)
        gui.removeNode()
        self.loaded = 1
        return

    def unload(self):
        if self.loaded:
            self.frame.destroy()
            del self.frame
            del self.statusFrame
            del self.textFrame
            del self.avatarButtons
            del self.backButton
        self.loaded = 0

    def enter(self, numAvatars, localNum = None, luredIndices = None, trappedIndices = None, track = None, fireCosts = None):
        if not self.loaded:
            self.load()
        self.frame.show()
        invalidTargets = []
        if not self.toon:
            self.adjustCogs(numAvatars, luredIndices, trappedIndices, track, fireCosts)
        else:
            self.adjustToons(numAvatars, localNum)

    def exit(self):
        self.frame.hide()

    def __handleBack(self):
        doneStatus = {'mode': 'Back'}
        messenger.send(self.doneEvent, [doneStatus])

    def __handleAvatar(self, avatar):
        doneStatus = {'mode': 'Avatar',
         'avatar': avatar}
        messenger.send(self.doneEvent, [doneStatus])

    def adjustCogs(self, numAvatars, luredIndices, trappedIndices, track, fireCosts):
        invalidTargets = []
        if len(luredIndices) > 0:
            if track == BattleBase.TRAP or track == BattleBase.LURE:
                invalidTargets += luredIndices
        if len(trappedIndices) > 0:
            if track == BattleBase.TRAP:
                invalidTargets += trappedIndices
        self.__placeButtons(numAvatars, invalidTargets, fireCosts=fireCosts)

    def adjustToons(self, numToons, localNum):
        self.__placeButtons(numToons, [], localNum)

    def __placeButtons(self, numAvatars, invalidTargets, localNum=-1, fireCosts=None):
        canfire = 0
        for i in xrange(SuitBattleGlobals.MAX_SUIT_CAPACITY):
            if i != localNum and i not in invalidTargets:
                self.avatarButtons[i].show()
                self.avatarButtons[i]['text'] = ''
                if not fireCosts or fireCosts[i] <= localAvatar.getPinkSlips():
                    self.avatarButtons[i]['state'] = DGG.NORMAL
                    self.avatarButtons[i]['text_fg'] = (0, 0, 0, 1)
                    canfire = 1
                else:
                    self.avatarButtons[i]['state'] = DGG.DISABLED
                    self.avatarButtons[i]['text_fg'] = (1.0, 0, 0, 1)
            else:
                self.avatarButtons[i].hide()

        if canfire:
            self.textFrame['text'] = TTLocalizer.FireCogTitle % localAvatar.getPinkSlips()
        else:
            self.textFrame['text'] = TTLocalizer.FireCogLowTitle % localAvatar.getPinkSlips()

        origin = 0.0 + ((numAvatars - 1) * 0.2)
        for i in xrange(numAvatars):
            self.avatarButtons[i].setX(origin - (i * 0.4))
        return None
