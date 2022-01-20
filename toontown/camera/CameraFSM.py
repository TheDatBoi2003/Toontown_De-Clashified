from pandac.PandaModules import *
from direct.directnotify import DirectNotifyGlobal
from direct.fsm.FSM import FSM
from direct.task import Task
from direct.showbase.InputStateGlobal import inputState
from toontown.camera import FPSCamera


class CameraFSM(FSM):

    def __init__(self, av):
        FSM.__init__(self, 'CameraFSM')
        self.av = av
        self.fpsCamera = FPSCamera.FPSCamera(self.av)
        self.currentCamera = None
        self._rmbToken = inputState.watchWithModifiers('RMB', 'mouse3')
        return

    def cleanup(self):
        FSM.cleanup(self)
        if hasattr(self, 'cameras'):
            self._rmbToken.release()
            del self._rmbToken
            self.ignoreAll()
            del self.currentCamera
            self.fpsCamera.destroy()
            del self.fpsCamera

    def __str__(self):
        outStr = FSM.__str__(self)
        outStr += '(currentCamera: %s)' % self.currentCamera
        return outStr

    def getCurrentCamera(self):
        return self.currentCamera

    def getFPSCamera(self):
        return self.fpsCamera

    def defaultFilter(self, request, args):
        if request != self.getCurrentOrNextState():
            return FSM.defaultFilter(self, request, args)
        return None

    def enterOff(self):
        self.currentCamera = None
        base.localAvatar.attachCamera()
        base.localAvatar.nudgeCamera()
        return

    def exitOff(self):
        pass

    def enterFPS(self):
        self.fpsCamera.start()
        self.currentCamera = self.fpsCamera

    def exitFPS(self):
        self.fpsCamera.stop()
