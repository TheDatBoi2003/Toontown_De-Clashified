from direct.gui.DirectGui import *
from direct.showbase.MessengerGlobal import messenger
from panda3d.core import *

import ShtikerPage
from toontown.shtiker import TrackSetDialog
from toontown.toonbase import TTLocalizer
from toontown.toonbase.ToontownBattleGlobals import TrackColors, TrackIcons, Tracks, AvPropsNew
from toontown.toonbase.ToontownGlobals import MinTrainingFrames, MaxTrainingFrames
from toontown.toontowngui import TTDialog

BASE_FRAMES = MinTrainingFrames
TOTAL_FRAMES = MaxTrainingFrames + 2
COLS = 6
ROWS = 3


def calcAvailableFrames(frames):
    count = 0
    for frame in frames:
        if frame == -1:
            count += 1
    return count


def calcUnlockedFrames(frames):
    count = 0
    for frame in frames:
        if frame != -2:
            count += 1
    return count


class TrackFrame(DirectFrame):

    def __init__(self, index):
        DirectFrame.__init__(self, relief=None)
        self.initialiseoptions(TrackFrame)
        filmstrip = loader.loadModel('phase_3.5/models/gui/filmstrip')
        guiButton = loader.loadModel('phase_3/models/gui/quit_button')
        buttons = loader.loadModel('phase_3/models/gui/dialog_box_buttons_gui')
        self.gags = loader.loadModel('phase_3.5/models/gui/inventory_icons')
        self.index = index
        self.frame = DirectFrame(parent=self, relief=None,
                                 image=filmstrip, image_scale=(6 / float(COLS), 6 / float(COLS), 3 / float(ROWS)),
                                 text=str(self.index + 1),
                                 sortOrder=DGG.BACKGROUND_SORT_INDEX,
                                 text_pos=(0.26, -0.22), text_fg=(1, 1, 1, 1), text_scale=0.1)
        self.question = DirectLabel(parent=self.frame, relief=None, pos=(0, 0, -0.15), text='?', text_scale=0.4,
                                    text_pos=(0, 0.04), text_fg=(0.72, 0.72, 0.72, 1))
        self.icon = DirectFrame(parent=self.frame, relief=None,
                                text='', text_pos=(0, 0.15), text_fg=(1, 1, 1, 1), text_scale=0.1)
        self.trackSetButton = DirectButton(parent=self.frame, relief=None,
                                           pos=(0.0, 0.0, 0.05),
                                           scale=2,
                                           image=(guiButton.find('**/QuitBtn_UP'),
                                                  guiButton.find('**/QuitBtn_DN'),
                                                  guiButton.find('**/QuitBtn_RLVR')),
                                           image3_color=Vec4(0.5, 0.5, 0.5, 0.5), image_scale=(0.7, 1, 1),
                                           text=TTLocalizer.TrackPageBtn,
                                           text3_fg=(0.5, 0.5, 0.5, 0.75),
                                           text_scale=0.06,
                                           text_pos=(0, -0.02),
                                           text_wordwrap=TTLocalizer.DSDintroTextWordwrap,
                                           text_align=TextNode.ACenter,
                                           command=self.__trackSet)
        self.refundButton = DirectButton(parent=self, relief=None, image=(buttons.find('**/CloseBtn_UP'),
                                                                          buttons.find('**/CloseBtn_DN'),
                                                                          buttons.find('**/CloseBtn_Rllvr')),
                                         pos=(0.26, 0, 0.20), command=self.__promptRefund)
        self.refundButton.hide()
        self.trackSetButton.hide()
        self.refundDialog = None
        filmstrip.removeNode()
        return

    def play(self, trackId):
        pass

    def setTrained(self, trackId):
        self.question.hide()
        self.trackSetButton.hide()
        if base.localAvatar.refundPoints > 0 or base.localAvatar.getTrainingFrames().count(trackId) == 1:
            self.refundButton.show()
        else:
            self.refundButton.hide()
        trackColorR, trackColorG, trackColorB = TrackColors[trackId]
        self.frame['image_color'] = Vec4(trackColorR * 0.75, trackColorG * 0.75, trackColorB * 0.75, 1)
        self.frame['text_fg'] = Vec4(1, 1, 1, 1)
        self.frame['text_shadow'] = Vec4(0, 0, 0, 1)
        self.icon.setImage(self.gags.find('**/' + AvPropsNew[trackId][TrackIcons[trackId]]))
        self.icon['image_scale'] = 2
        self.icon['image_pos'] = (0, 0, -0.05)
        self.icon['text'] = Tracks[trackId].upper()
        self.icon['text_fg'] = Vec4(trackColorR * 0.2, trackColorG * 0.2, trackColorB * 0.2, 1)
        return

    def setUntrained(self, unlocked):
        self.refundButton.hide()
        if unlocked:
            self.question.hide()
            self.trackSetButton.show()
            self.frame['image_color'] = Vec4(0.3, 0.5, 0.9, 1)
            self.frame['text_fg'] = Vec4(0.3, 0.3, 0.3, 1)
            self.frame['text_shadow'] = Vec4(0.3, 0.3, 0.3, 0)
            self.icon.clearImage()
            self.question['text_fg'] = Vec4(0.06, 0.2, 0.6, 1)
        else:
            self.question.show()
            self.trackSetButton.hide()
            self.frame['image_color'] = Vec4(0.7, 0.7, 0.7, 1)
            self.frame['text_fg'] = Vec4(0.5, 0.5, 0.5, 1)
            self.frame['text_shadow'] = Vec4(0.3, 0.3, 0.3, 0)
            self.icon.clearImage()
            self.question['text_fg'] = Vec4(0.6, 0.6, 0.6, 1)
        self.icon['image'] = None
        self.icon['text'] = ''

    def __trackSet(self):
        messenger.send('track-set', [self.index])

    def __promptRefund(self):
        if self.refundDialog is None:
            frames = base.localAvatar.getTrainingFrames()
            trackCount = frames.count(frames[self.index])
            if trackCount == 3:
                prompt = TTLocalizer.TrackRefundPrestigePrompt
            elif trackCount == 2:
                prompt = TTLocalizer.TrackRefundAccessPrompt
            else:
                prompt = TTLocalizer.TrackRefundPrompt
            self.refundDialog = TTDialog.TTDialog(dialogName='TrackSetApply',
                                                  style=TTDialog.TwoChoice,
                                                  text=prompt,
                                                  text_wordwrap=15,
                                                  sortOrder=DGG.FOREGROUND_SORT_INDEX + 999,
                                                  command=self.__refundDone)
            self.refundDialog.setBin('gui-popup', 0)
            base.transitions.fadeScreen(0.5)

    def __refundDone(self, command):
        self.refundDialog.clearBin()
        self.refundDialog.cleanup()
        self.refundDialog = None
        if command != DGG.DIALOG_OK:
            return
        base.localAvatar.d_validateRefund(self.index)


class TrackPage(ShtikerPage.ShtikerPage):

    def __init__(self):
        ShtikerPage.ShtikerPage.__init__(self)
        self.trackFrames = []

    def placeFrames(self):
        rowY = 0.32
        rowSpace = -0.96 / ROWS
        rowPos = []
        for i in xrange(ROWS):
            rowPos.append(rowY)
            rowY += rowSpace

        colX = -0.7
        colSpace = 1.656 / COLS
        colPos = []
        for i in xrange(COLS):
            colPos.append(colX)
            colX += colSpace

        for index in xrange(1, TOTAL_FRAMES + 1):
            frame = self.trackFrames[index - 1]
            col = (index - 1) % COLS
            row = (index - 1) / COLS
            frame.setPos(colPos[col], 0, rowPos[row])
            frame.setScale(0.39)

    def load(self):
        self.title = DirectLabel(parent=self, relief=None, text=TTLocalizer.TrackPageTitle, text_scale=0.1,
                                 pos=(0, 0, 0.6))
        self.subtitle = DirectLabel(parent=self, relief=None, text=TTLocalizer.TrackPageSubtitle, text_scale=0.05,
                                    text_fg=(0.5, 0.1, 0.1, 1), pos=(0, 0, 0.5))
        self.trackText = DirectLabel(parent=self, relief=None, text='', text_scale=0.05, text_fg=(0.5, 0.1, 0.1, 1),
                                     pos=(0, 0, -0.6))
        for index in xrange(TOTAL_FRAMES):
            frame = TrackFrame(index - 1)
            frame.reparentTo(self)
            self.trackFrames.append(frame)

        self.placeFrames()
        self.startFrame = self.trackFrames[0]
        self.endFrame = self.trackFrames[-1]
        self.startFrame.frame['text'] = ''
        self.startFrame.frame['text_scale'] = TTLocalizer.TPstartFrame
        self.startFrame.frame['image_color'] = Vec4(0.2, 0.2, 0.2, 1)
        self.startFrame.frame['text_fg'] = (1, 1, 1, 1)
        self.startFrame.frame['text_pos'] = (0, 0.025)
        self.startFrame.frame['text_align'] = TextNode.ACenter
        self.startFrame.icon['image'] = None
        self.startFrame.question.hide()
        self.endFrame.frame['text'] = ''
        self.endFrame.frame['text_scale'] = TTLocalizer.TPendFrame
        self.endFrame.frame['image_color'] = Vec4(0.2, 0.2, 0.2, 1)
        self.endFrame.frame['text_fg'] = (1, 1, 1, 1)
        self.endFrame.frame['text_pos'] = (0, 0.025)
        self.endFrame.icon['image'] = None
        self.endFrame.question.hide()
        self.trackSetMenu = None
        self.accept('track-set', self.__openTrackSelection)
        return

    def unload(self):
        self.__closeTrackSelection()
        del self.title
        del self.subtitle
        del self.trackText
        del self.trackFrames
        ShtikerPage.ShtikerPage.unload(self)

    def clearPage(self):
        for index in xrange(1, TOTAL_FRAMES - 1):
            self.trackFrames[index].setUntrained(0)

        self.subtitle.show()
        self.startFrame.frame['text'] = ''
        self.endFrame.frame['text'] = ''
        self.trackText['text'] = TTLocalizer.TrackPageFull
        if self.trackSetMenu:
            self.__closeTrackSelection()

    def updatePage(self):
        trainingFrames = base.localAvatar.getTrainingFrames()
        if len(trainingFrames) >= BASE_FRAMES:
            availableFrames = calcAvailableFrames(trainingFrames)
            unlockedFrames = calcUnlockedFrames(trainingFrames)
            if unlockedFrames == MaxTrainingFrames:
                self.subtitle.hide()
            else:
                self.subtitle.show()
            if availableFrames:
                self.trackText['text'] = TTLocalizer.TrackPageAvailable % \
                                     (availableFrames, TTLocalizer.TrackPageFrame[availableFrames != 1])
            else:
                self.trackText['text'] = TTLocalizer.TrackPageFull
            self.startFrame.frame['text'] = TTLocalizer.TrackPageFilmTitle % unlockedFrames
            if base.localAvatar.refundPoints:
                self.endFrame.frame['text'] = TTLocalizer.TrackPageRefundCount % base.localAvatar.refundPoints
            else:
                self.endFrame.frame['text'] = TTLocalizer.TrackPageNoRefunds
            for index in xrange(0, MaxTrainingFrames):
                if trainingFrames[index] > -1:
                    self.trackFrames[index + 1].setTrained(trainingFrames[index])
                else:
                    self.trackFrames[index + 1].setUntrained(trainingFrames[index] != -2)
        else:
            self.clearPage()

    def enter(self):
        self.updatePage()
        ShtikerPage.ShtikerPage.enter(self)

    def exit(self):
        self.clearPage()
        ShtikerPage.ShtikerPage.exit(self)

    def __openTrackSelection(self, index):
        if self.trackSetMenu is None:
            self.trackSetMenu = TrackSetDialog.TrackSetDialog()
            self.trackSetMenu.load()
        self.trackSetMenu.enter(index)
        self.accept('chosen-track', self.__choseTrackFrame)
        self.accept('close-track-selection', self.__closeTrackSelection)

    def __choseTrackFrame(self, chosenTrack, frameNum):
        base.localAvatar.d_validateTrackChoice(chosenTrack, frameNum)
        self.ignore('chosen-track')
        self.__closeTrackSelection()
        self.updatePage()

    def __closeTrackSelection(self):
        if self.trackSetMenu:
            self.ignore('close-track-selection')
            self.trackSetMenu.unload()
