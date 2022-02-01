from panda3d.core import *
import ShtikerPage
from direct.gui.DirectGui import *
from toontown.quest import Quests
from toontown.toonbase import ToontownGlobals
from toontown.toonbase import ToontownBattleGlobals
from toontown.toonbase import TTLocalizer
from toontown.toon import Toon
from toontown.toonbase.ToontownBattleGlobals import TrackIcons, AvPropsNew

BASE_FRAMES = ToontownBattleGlobals.MIN_TRACK_FRAMES
MAX_FRAMES = ToontownBattleGlobals.MAX_TRACK_FRAMES + 2
COLS = 6
ROWS = 3


class TrackFrame(DirectFrame):

    def __init__(self, index):
        DirectFrame.__init__(self, relief=None)
        self.initialiseoptions(TrackFrame)
        filmstrip = loader.loadModel('phase_3.5/models/gui/filmstrip')
        self.gags = loader.loadModel('phase_3.5/models/gui/inventory_icons')
        self.index = index
        self.frame = DirectFrame(parent=self, relief=None,
                                 image=filmstrip, image_scale=(6 / float(COLS), 6 / float(COLS), 3 / float(ROWS)),
                                 text=str(self.index - 1),
                                 text_pos=(0.26, -0.22), text_fg=(1, 1, 1, 1), text_scale=0.1)
        self.question = DirectLabel(parent=self.frame, relief=None, pos=(0, 0, -0.15), text='?', text_scale=0.4, text_pos=(0, 0.04), text_fg=(0.72, 0.72, 0.72, 1))
        self.icon = DirectFrame(parent=self.frame, relief=None,
                                image=None, image_scale=1,
                                text='', text_pos=(0, -0.2), text_fg=(1, 1, 1, 1), text_scale=0.3)
        filmstrip.removeNode()
        return

    def play(self, trackId):
        pass

    def setTrained(self, trackId):
        self.question.hide()
        trackColorR, trackColorG, trackColorB = ToontownBattleGlobals.TrackColors[trackId]
        self.frame['image_color'] = Vec4(trackColorR, trackColorG, trackColorB, 1)
        self.frame['text_fg'] = Vec4(trackColorR * 0.3, trackColorG * 0.3, trackColorB * 0.3, 1)
        self.icon['image'] = self.gags.find('**/' + AvPropsNew[trackId][TrackIcons[trackId]])
        self.icon['text'] = ToontownBattleGlobals.Tracks[trackId].capitalize()
        return

    def setUntrained(self, available):
        self.question.show()
        if available:
            self.frame['image_color'] = Vec4(0.1, 0.5, 0.9, 1)
            self.frame['text_fg'] = Vec4(0.3, 0.3, 0.3, 1)
            self.question['text_fg'] = Vec4(0.06, 0.2, 0.6, 1)
        else:
            self.frame['image_color'] = Vec4(0.7, 0.7, 0.7, 1)
            self.frame['text_fg'] = Vec4(0.5, 0.5, 0.5, 1)
            self.question['text_fg'] = Vec4(0.6, 0.6, 0.6, 1)
        self.icon['image'] = None
        self.icon['text'] = ''


class TrackPage(ShtikerPage.ShtikerPage):

    def __init__(self):
        ShtikerPage.ShtikerPage.__init__(self)
        self.trackFrames = []

    def placeFrames(self):
        rowY = 0.38
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

        for index in xrange(1, MAX_FRAMES + 1):
            frame = self.trackFrames[index - 1]
            col = (index - 1) % COLS
            row = (index - 1) / COLS
            frame.setPos(colPos[col], 0, rowPos[row])
            frame.setScale(0.39)

    def load(self):
        self.title = DirectLabel(parent=self, relief=None, text=TTLocalizer.TrackPageTitle, text_scale=0.1, pos=(0, 0, 0.65))
        self.subtitle = DirectLabel(parent=self, relief=None, text=TTLocalizer.TrackPageSubtitle, text_scale=0.05, text_fg=(0.5, 0.1, 0.1, 1), pos=(0, 0, 0.56))
        self.trackText = DirectLabel(parent=self, relief=None, text='', text_scale=0.05, text_fg=(0.5, 0.1, 0.1, 1), pos=(0, 0, -0.5))
        for index in xrange(1, MAX_FRAMES + 1):
            frame = TrackFrame(index)
            frame.reparentTo(self)
            self.trackFrames.append(frame)

        self.placeFrames()
        self.startFrame = self.trackFrames[0]
        self.endFrame = self.trackFrames[-1]
        self.startFrame.frame['text'] = ''
        self.startFrame.frame['text_scale'] = TTLocalizer.TPstartFrame
        self.startFrame.frame['image_color'] = Vec4(0.2, 0.2, 0.2, 1)
        self.startFrame.frame['text_fg'] = (1, 1, 1, 1)
        self.startFrame.frame['text_pos'] = (0, 0.08)
        self.startFrame.question.hide()
        self.endFrame.frame['text'] = TTLocalizer.TrackPageDone
        self.endFrame.frame['text_scale'] = TTLocalizer.TPendFrame
        self.endFrame.frame['image_color'] = Vec4(0.2, 0.2, 0.2, 1)
        self.endFrame.frame['text_fg'] = (1, 1, 1, 1)
        self.endFrame.frame['text_pos'] = (0, 0)
        self.endFrame.question.hide()
        return

    def unload(self):
        del self.title
        del self.subtitle
        del self.trackText
        del self.trackFrames
        ShtikerPage.ShtikerPage.unload(self)

    def clearPage(self):
        for index in xrange(1, MAX_FRAMES - 1):
            self.trackFrames[index].setUntrained(0)

        self.startFrame.frame['text'] = ''
        self.trackText['text'] = TTLocalizer.TrackPageFull

    def updatePage(self):
        trackIds, trainingFrames = base.localAvatar.getTrainingFrames()
        if trainingFrames <= BASE_FRAMES:
            self.clearPage()
        else:
            self.trackText['text'] = TTLocalizer.TrackPageAvailable % trainingFrames
            trainingFramesArray = base.localAvatar.getTrackProgressAsArray()
            for index in xrange(1, MAX_FRAMES):
                if trainingFramesArray[index - 1]:
                    self.trackFrames[index].setTrained(trackIds[index])
                else:
                    self.trackFrames[index].setUntrained(trackIds[index] != -1)
            self.startFrame.frame['text'] = TTLocalizer.TrackPageFilmTitle % trainingFrames

    def enter(self):
        self.updatePage()
        ShtikerPage.ShtikerPage.enter(self)

    def exit(self):
        self.clearPage()
        ShtikerPage.ShtikerPage.exit(self)
