from panda3d.core import *
from toontown.toon import ToonDNA
from direct.fsm import StateData
from direct.gui.DirectGui import *
from toontown.makeatoon.MakeAToonGlobals import *
from toontown.toonbase import TTLocalizer, ToontownGlobals
from direct.directnotify import DirectNotifyGlobal
from direct.task import Task

from toontown.toonbase.ToontownBattleGlobals import MAX_TRACK_INDEX, AvPropsNew, TrackIcons


class StartingTrackShop(StateData.StateData):
    notify = DirectNotifyGlobal.directNotify.newCategory('StatusShop')

    def __init__(self, doneEvent):
        StateData.StateData.__init__(self, doneEvent)
        self.toon = None
        self.index = 0
        self.tracks = [0 for _ in xrange(MAX_TRACK_INDEX + 1)]
        self.optionsLeft = 2

    def enter(self, toon, shopsVisited = []):
        base.disableMouse()
        self.toon = toon
        self.dna = toon.getStyle()
        self.acceptOnce('last', self.__handleBackward)
        self.acceptOnce('next', self.__handleForward)

    def showButtons(self, nextButton):
        self.nextButton = nextButton
        self.parentFrame.show()
        self.__updateNext()

    def hideButtons(self):
        self.parentFrame.hide()

    def exit(self):
        self.ignore('last')
        self.ignore('next')
        try:
            del self.toon
        except:
            print 'StatusShop: toon not found'

        self.hideButtons()

    def load(self):
        normalTextColor = (0.3, 0.25, 0.2, 1)
        self.gui = loader.loadModel('phase_3/models/gui/tt_m_gui_mat_mainGui')
        self.gags = loader.loadModel('phase_3.5/models/gui/inventory_icons')
        guiRArrowUp = self.gui.find('**/tt_t_gui_mat_arrowUp')
        guiRArrowRollover = self.gui.find('**/tt_t_gui_mat_arrowUp')
        guiRArrowDown = self.gui.find('**/tt_t_gui_mat_arrowDown')
        guiRArrowDisabled = self.gui.find('**/tt_t_gui_mat_arrowDisabled')
        shuffleFrame = self.gui.find('**/tt_t_gui_mat_shuffleFrame')
        shuffleUp = self.gui.find('**/tt_t_gui_mat_shuffleUp')
        shuffleDown = self.gui.find('**/tt_t_gui_mat_shuffleDown')
        shuffleImage = (self.gui.find('**/tt_t_gui_mat_shuffleArrowUp'), self.gui.find('**/tt_t_gui_mat_shuffleArrowDown'), self.gui.find('**/tt_t_gui_mat_shuffleArrowUp'), self.gui.find('**/tt_t_gui_mat_shuffleArrowDisabled'))
        bookModel = loader.loadModel('phase_3.5/models/gui/stickerbook_gui')
        poster = bookModel.find('**/questCard')
        checkedImage = self.gui.find('**/tt_t_gui_mat_okUp')
        uncheckedImage = self.gui.find('**/tt_t_gui_mat_okDown')
        self.parentFrame = self.getNewFrame()
        self.trackFrame = DirectFrame(parent=self.parentFrame, relief=None,
                                      pos=(0, 0, -0.11), hpr=(0, 0, -2), scale=1.1,
                                      image=shuffleFrame, image_scale=halfButtonInvertScale, frameColor=(1, 1, 1, 1),
                                      text='', text_scale=0.0625, text_pos=(-0.001, -0.015), text_fg=(1, 1, 1, 1))
        self.trackLButton = DirectButton(parent=self.trackFrame, relief=None, pos=(-0.2, 0, 0),
                                         image=shuffleImage, image_scale=halfButtonScale,
                                         image1_scale=halfButtonHoverScale,
                                         image2_scale=halfButtonHoverScale,
                                         command=self.__swapTrackSelection, extraArgs=[-1])
        self.trackRButton = DirectButton(parent=self.trackFrame, relief=None, pos=(0.2, 0, 0),
                                         image=shuffleImage, image_scale=halfButtonInvertScale,
                                         image1_scale=halfButtonInvertHoverScale,
                                         image2_scale=halfButtonInvertHoverScale,
                                         command=self.__swapTrackSelection, extraArgs=[1])
        self.trackInfo = DirectFrame(parent=self.trackFrame, relief=None, pos=(0, 0, -0.4),
                                     image=poster, image_scale=(0.7, 0.7, 0.7), image_pos=(0, 0, -0.05),
                                     text='', text_font=ToontownGlobals.getInterfaceFont(), text_fg=normalTextColor,
                                     text_scale=0.05, text_wordwrap=12.0)
        self.gagIcon = DirectFrame(parent=self.trackInfo, relief=None, pos=(0.0, 1.5, 0.125), scale=1.0,
                                   image_pos=(0, 0, 0), image_scale=(0.4, 1, 0.4), image_color=(1, 1, 1, 1),
                                   text='', text_font=ToontownGlobals.getInterfaceFont(), text_scale=0.06,
                                   text_pos=(0, 0.1), textMayChange=1)
        self.toggleButton = DirectCheckButton(parent=self.trackInfo, pos=(-0.35, 0, -0.18), scale=(0.7, 0.7, 0.1), relief=None,
                                              boxImage=(uncheckedImage, checkedImage, None),
                                              boxImageScale=(0.7, 0.7, 4.9), boxRelief=None,
                                              boxPlacement='right',
                                              command=self.__clickCallback, indicator_pos=(0.8, 0.0, -0.075),
                                              text='', text_font=ToontownGlobals.getInterfaceFont(),
                                              text_pos=(0.35, 0, 0),
                                              text_fg=normalTextColor, text_scale=(0.07, 0.49), text_wordwrap=6.0)
        self.__swapTrackSelection(0)
        self.parentFrame.hide()

    def unload(self):
        self.gui.removeNode()
        del self.gui
        self.parentFrame.destroy()
        del self.parentFrame
        self.ignore('MAT-newToonCreated')
    
    def getNewFrame(self):
        frame = DirectFrame(relief=DGG.RAISED, pos=(0.98, 0, 0.416), frameColor=(1, 0, 0, 0))
        frame.setPos(-0.66, 0, -0.5)
        frame.reparentTo(base.a2dTopRight)
        return frame

    def __swapTrackSelection(self, direction):
        self.index += direction
        if self.index <= 0:
            self.index = 0
            self.trackLButton['state'] = DGG.DISABLED
            self.trackRButton['state'] = DGG.NORMAL
        elif self.index >= MAX_TRACK_INDEX:
            self.index = MAX_TRACK_INDEX
            self.trackLButton['state'] = DGG.NORMAL
            self.trackRButton['state'] = DGG.DISABLED
        else:
            self.trackLButton['state'] = DGG.NORMAL
            self.trackRButton['state'] = DGG.NORMAL
        self.toggleButton['indicatorValue'] = self.tracks[self.index]
        if self.optionsLeft or self.tracks[self.index]:
            self.toggleButton['state'] = DGG.NORMAL
            self.toggleButton['text'] = TTLocalizer.TrackAvailable[0]
            self.toggleButton['text_pos'] = (0.35, 0, 0)
            self.toggleButton['text_wordwrap'] = 6.0
            self.toggleButton.indicator.show()
        else:
            self.toggleButton['state'] = DGG.DISABLED
            self.toggleButton['text'] = TTLocalizer.TrackAvailable[1]
            self.toggleButton['text_pos'] = (0.5, 0, 0)
            self.toggleButton['text_wordwrap'] = 12.0
            self.toggleButton.indicator.hide()
        self.toggleButton.setIndicatorValue()
        self.trackFrame['text'] = TTLocalizer.TrackTitles[self.index]
        self.trackInfo['text'] = TTLocalizer.TrackInfos[self.index]
        self.gagIcon['image'] = self.gags.find('**/' + AvPropsNew[self.index][TrackIcons[self.index]])

    def __updateNext(self):
        if self.optionsLeft != 0:
            self.nextButton.hide()
        else:
            self.nextButton.show()

    def __handleForward(self):
        self.doneStatus = 'next'
        messenger.send(self.doneEvent)

    def __handleBackward(self):
        self.doneStatus = 'last'
        messenger.send(self.doneEvent)

    def __clickCallback(self, value):
        if value and self.optionsLeft > 0:
            self.tracks[self.index] = value
            self.optionsLeft -= 1
            if self.toon:
                self.toon.choices[self.optionsLeft] = self.index
        else:
            self.tracks[self.index] = value
            self.optionsLeft += 1
            if self.toon:
                self.toon.choices[self.optionsLeft] = -1
        self.__updateNext()