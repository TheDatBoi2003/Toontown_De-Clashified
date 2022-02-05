from direct.gui.DirectGui import *
from direct.showbase.MessengerGlobal import messenger
from panda3d.core import *
from libotp import *
from direct.task.Task import Task
from direct.fsm import StateData
from direct.showbase import AppRunnerGlobal
from direct.directnotify import DirectNotifyGlobal
from toontown.toonbase import TTLocalizer
from toontown.toonbase.ToontownBattleGlobals import Tracks
from toontown.toontowngui import TTDialog
from toontown.toonbase import ToontownGlobals
from toontown.toonbase.DisplayOptions import DisplayOptions


class TrackSetDialog(DirectFrame, StateData.StateData):
    notify = DirectNotifyGlobal.directNotify.newCategory('TrackSetDialog')

    def __init__(self):
        DirectFrame.__init__(self, pos=(0, 0, 0.3), relief=None, image=DGG.getDefaultDialogGeom(),
                             image_scale=(1.6, 1, 1.2), image_pos=(0, 0, -0.05),
                             image_color=ToontownGlobals.GlobalDialogColor, text=TTLocalizer.TrackSetTitle,
                             text_scale=0.12, text_pos=(0, 0.4), borderWidth=(0.01, 0.01))
        StateData.StateData.__init__(self, 'track-set-done')

        self.infoText = DirectLabel(parent=self, relief=None, scale=TTLocalizer.DSDintroText, pos=(-0.725, 0, 0.3),
                                    text=TTLocalizer.TrackSetInfo,
                                    text_wordwrap=TTLocalizer.DSDintroTextWordwrap,
                                    text_align=TextNode.ALeft)

        guiButton = loader.loadModel('phase_3/models/gui/quit_button')
        self.trackButtons = []
        for i in xrange(len(Tracks)):
            posx = -0.6 + 0.4 * (i % 4)
            posz = -0.05 - 0.2 * (i / 4)
            self.trackButtons.append(DirectButton(parent=self, relief=None, pos=(posx, 0, posz),
                                                  image=(guiButton.find('**/QuitBtn_UP'),
                                                         guiButton.find('**/QuitBtn_DN'),
                                                         guiButton.find('**/QuitBtn_RLVR')),
                                                  image_scale=(0.6, 1, 1),
                                                  text=Tracks[i].upper(),
                                                  text_scale=0.06,
                                                  text_pos=(0, -0.02),
                                                  command=self.__chooseTrack,
                                                  extraArgs=[i]))
        self.cancel = DirectButton(parent=self, relief=None, pos=(0, 0, -0.53),
                                   image=(guiButton.find('**/QuitBtn_UP'),
                                          guiButton.find('**/QuitBtn_DN'),
                                          guiButton.find('**/QuitBtn_RLVR')),
                                   image_scale=(0.6, 1, 1),
                                   text=TTLocalizer.DisplaySettingsCancel,
                                   text_scale=0.06,
                                   text_pos=(0, -0.02),
                                   command=self.__cancel)

        guiButton.removeNode()
        self.initialiseoptions(TrackSetDialog)
        self.chosenTrack = None
        self.chosenTrackName = None
        self.frameNum = None
        return

    def unload(self):
        if self.isLoaded == 0:
            return None
        self.isLoaded = 0
        self.exit()
        self.hide()
        return None

    def load(self):
        if self.isLoaded == 1:
            return None
        self.isLoaded = 1
        self.setBin('gui-popup', 0)
        self.hide()
        return

    def enter(self, frameNum=0):
        if self.isEntered == 1:
            return None
        self.isEntered = 1
        if self.isLoaded == 0:
            self.load()
        self.applyDialog = None
        base.transitions.fadeScreen(0.5)
        self.frameNum = frameNum
        self.show()
        return

    def exit(self):
        if self.isEntered == 0:
            return None
        if self.isLoaded:
            self.unload()
        self.isEntered = 0
        self.cleanupDialogs()
        base.transitions.noTransitions()
        self.ignoreAll()
        return None

    def cleanupDialogs(self):
        if self.applyDialog:
            self.applyDialog.cleanup()
            self.applyDialog = None
        return

    def __chooseTrack(self, trackNum):
        self.chosenTrack = trackNum
        self.chosenTrackName = Tracks[trackNum].upper()
        self.cleanupDialogs()
        self.clearBin()
        self.applyDialog = TTDialog.TTDialog(dialogName='TrackSetApply', style=TTDialog.TwoChoice,
                                             text=TTLocalizer.TrackSetConfirmation % self.chosenTrackName,
                                             text_wordwrap=15, command=self.__applyDone)
        self.applyDialog.setBin('gui-popup', 0)

    def __applyDone(self, command):
        self.applyDialog.clearBin()
        self.applyDialog.cleanup()
        self.applyDialog = None
        if command != DGG.DIALOG_OK:
            return
        messenger.send('chosen-track', [self.chosenTrack, self.frameNum])
        self.exit()

    def __cancel(self):
        messenger.send('close-track-selection')
        self.exit()
