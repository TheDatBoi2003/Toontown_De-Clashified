from direct.showbase.InputStateGlobal import inputState

from toontown.toonbase import ToontownGlobals
from toontown.toonbase.ToontownGlobals import *
from direct.directnotify import DirectNotifyGlobal
import Walk

class PublicWalk(Walk.Walk):
    notify = DirectNotifyGlobal.directNotify.newCategory('PublicWalk')

    def __init__(self, parentFSM, doneEvent):
        Walk.Walk.__init__(self, doneEvent)
        self.parentFSM = parentFSM
        self.lastFov = base.localAvatar.fov

    def load(self):
        Walk.Walk.load(self)

    def unload(self):
        Walk.Walk.unload(self)
        del self.parentFSM

    def enter(self, slowWalk = 0):
        Walk.Walk.enter(self, slowWalk)
        base.localAvatar.book.showButton()
        self.accept(StickerBookHotkey, self.__handleStickerBookEntry)
        self.accept('enterStickerBook', self.__handleStickerBookEntry)
        self.accept(OptionsPageHotkey, self.__handleOptionsEntry)
        self.accept(base.SPRINT, self.__startSprintCheck)
        self.accept(base.SPRINT + '-up', self.__exitSprint)
        base.localAvatar.laffMeter.start()
        base.localAvatar.beginAllowPies()
        if base.wantNewCamera:
            base.localAvatar.cameraFSM.request('FPS')

    def exit(self):
        Walk.Walk.exit(self)
        base.localAvatar.book.hideButton()
        self.ignore(StickerBookHotkey)
        self.ignore('enterStickerBook')
        self.ignore(OptionsPageHotkey)
        self.ignore(base.SPRINT)
        self.ignore(base.SPRINT + '-up')
        base.localAvatar.laffMeter.stop()
        base.localAvatar.endAllowPies()
        if base.wantNewCamera:
            base.localAvatar.cameraFSM.request('Off')

    def __handleStickerBookEntry(self):
        currentState = base.localAvatar.animFSM.getCurrentState().getName()
        if currentState == 'jumpAirborne':
            return
        if base.localAvatar.book.isObscured():
            return
        else:
            doneStatus = {}
            doneStatus['mode'] = 'StickerBook'
            messenger.send(self.doneEvent, [doneStatus])
            return

    def __handleOptionsEntry(self):
        currentState = base.localAvatar.animFSM.getCurrentState().getName()
        if currentState == 'jumpAirborne':
            return
        if base.localAvatar.book.isObscured():
            return
        else:
            doneStatus = {}
            doneStatus['mode'] = 'Options'
            messenger.send(self.doneEvent, [doneStatus])
            return

    def __startSprintCheck(self):
        if not hasattr(base.localAvatar, 'sprintMultiplier'):
            pass
        taskMgr.add(self.__sprintCheckTask, 'sprint-check-%d' % base.localAvatar.getDoId(), priority=-30)

    def __endSprintCheck(self):
        taskMgr.remove('sprint-check-%d' % base.localAvatar.getDoId())

    def __sprintCheckTask(self, task):
        if not base.localAvatar.movingFlag:
            return task.cont
        self.__enterSprint()
        return task.cont

    def __enterSprint(self):
        self.__endSprintCheck()
        self.lastFov = base.localAvatar.fov
        base.localAvatar.setWalkSpeedSprint()
        base.localAvatar.lerpCameraFov(base.localAvatar.fov * 1.2, 0.3)
        base.localAvatar.startSprintTask()

    def __exitSprint(self):
        if not hasattr(base.localAvatar, 'sprintMultiplier'):
            return
        self.__endSprintCheck()
        base.localAvatar.endSprintTask()
        base.localAvatar.setWalkSpeedNormal()
        base.localAvatar.lerpCameraFov(self.lastFov, 0.8)

