from pandac.PandaModules import *
from direct.showbase.InputStateGlobal import inputState
from direct.directnotify import DirectNotifyGlobal
from direct.interval.IntervalGlobal import *
from direct.showbase.PythonUtil import reduceAngle, fitSrcAngle2Dest, clamp, lerp
from direct.task import Task
from otp.otpbase import OTPGlobals
from otp.otpbase.PythonUtil import ParamObj
from toontown.camera import CameraMode
from toontown.toonbase import ToontownGlobals


class FPSCamera(CameraMode.CameraMode, NodePath, ParamObj):
    notify = DirectNotifyGlobal.directNotify.newCategory('FPSCamera')

    UpdateTaskName = 'FPSCamUpdateTask'
    ReadMouseTaskName = 'FPSCamReadMouseTask'
    CollisionCheckTaskName = 'FPSCamCollisionTask'
    MinP = -50
    MaxP = 20
    baseH = None
    minH = None
    maxH = None
    Sensitivity = base.CAM_SENSITIVITY

    def __init__(self, avatar, params=None):
        ParamObj.__init__(self)
        NodePath.__init__(self, 'fpsCam')
        CameraMode.CameraMode.__init__(self)
        self.avatar = avatar
        self.mouseX = 0.0
        self.mouseY = 0.0
        self._paramStack = []
        self._hadMouse = False
        self._getDefaultOffsets()
        self.camOffset = self._defaultOffset
        if params is None:
            self.setDefaultParams()
        else:
            params.applyTo(self)

        self.zIval = None
        self.camIval = None
        self.forceMaxDistance = True
        self.avFacingScreen = False

    def _getDefaultOffsets(self):
        try:
            self._defaultZ = base.localAvatar.getClampedAvatarHeight()
        except:
            self._defaultZ = 2.5
        self._defaultDistance = -3.0 * self._defaultZ
        self._minDistance = -self._defaultZ
        self._maxDistance = -8.94427191 * self._defaultZ
        self._zoomIncrement = self._defaultZ * (1.0 / 3.0)
        self._defaultOffset = Vec3(0, self._defaultDistance, self._defaultZ)

    def destroy(self):
        if self.zIval:
            self.zIval.finish()
            self.zIval = None

        if self.camIval:
            self.camIval.finish()
            self.camIval = None

        del self.avatar
        NodePath.removeNode(self)
        ParamObj.destroy(self)
        CameraMode.CameraMode.destroy(self)

    def getName(self):
        return 'FPS'

    def _getTopNodeName(self):
        return 'FPSCam'

    def enterActive(self):
        CameraMode.CameraMode.enterActive(self)
        base.camNode.setLodCenter(self.avatar)

        self._getDefaultOffsets()
        self.camOffset = self._defaultOffset
        self.accept('wheel_up', self._handleWheelUp)
        self.accept('wheel_down', self._handleWheelDown)
        self._resetWheel()
        self.reparentTo(self.avatar)
        self.setPos(0, 0, self._defaultZ)
        self.setH(0)
        self.setP(0)
        camera.reparentTo(self)
        camera.setPos(self.camOffset[0], self.camOffset[1], 0)
        camera.setHpr(0, 0, 0)
        self._startCollisionCheck()
        base.camLens.setMinFov(ToontownGlobals.DefaultCameraFov / (4. / 3.))

    def exitActive(self):
        if self.camIval:
            self.camIval.finish()
            self.camIval = None

        self.ignore('wheel_up')
        self.ignore('wheel_down')
        self._resetWheel()
        self._stopCollisionCheck()
        base.camNode.setLodCenter(NodePath())

        CameraMode.CameraMode.exitActive(self)

    def enableMouseControl(self):
        CameraMode.CameraMode.enableMouseControl(self)
        self.avatar.controlManager.setWASDTurn(0)

    def disableMouseControl(self):
        CameraMode.CameraMode.disableMouseControl(self)
        self.avatar.controlManager.setWASDTurn(1)

    def isSubjectMoving(self):
        return (inputState.isSet('forward') or inputState.isSet('reverse')
                or inputState.isSet('turnRight') or inputState.isSet('turnLeft')
                or inputState.isSet('slideRight') or inputState.isSet('slideLeft'))\
               and self.avatar.controlManager.isEnabled

    def _avatarFacingTask(self, task):
        if hasattr(base, 'oobeMode') and base.oobeMode:
            return task.cont

        if self.avFacingScreen:
            return task.cont

        if self.isSubjectMoving():
            camH = self.getH(render)
            subjectH = self.avatar.getH(render)
            if abs(camH - subjectH) > 0.01:
                self.avatar.setH(render, camH)
                self.setH(0)

        return task.cont

    def _mouseUpdateTask(self, task):
        if hasattr(base, 'oobeMode') and base.oobeMode:
            return task.cont
        if self.isSubjectMoving():
            hNode = self.avatar
        else:
            hNode = self

        if self.mouseDelta[0] or self.mouseDelta[1]:
            dx, dy = self.mouseDelta

            hNode.setH(hNode, -dx * self.Sensitivity[0])
            curP = self.getP()
            newP = curP + -dy * self.Sensitivity[1]
            newP = min(max(newP, self.MinP), self.MaxP)
            self.setP(newP)
            if self.baseH:
                self._checkHBounds(hNode)

            self.setR(render, 0)

        return task.cont

    def setHBounds(self, baseH, minH, maxH):
        self.baseH = baseH
        self.minH = minH
        self.maxH = maxH
        if self.isSubjectMoving():
            hNode = self.avatar
        else:
            hNode = self

        hNode.setH(maxH)

    def clearHBounds(self):
        self.baseH = self.minH = self.maxH = None

    def _checkHBounds(self, hNode):
        currH = fitSrcAngle2Dest(hNode.getH(), 180)
        if currH < self.minH:
            hNode.setH(reduceAngle(self.minH))
        elif currH > self.maxH:
            hNode.setH(reduceAngle(self.maxH))

    def _handleWheelUp(self):
        yDist = self.camOffset[1] + self._zoomIncrement
        self._zoomToDistance(yDist)

    def _handleWheelDown(self):
        yDist = self.camOffset[1] - self._zoomIncrement
        self._zoomToDistance(yDist)

    def _zoomToDistance(self, yDist):
        y = clamp(yDist, self._minDistance, self._maxDistance)
        self.camOffset.setY(y)
        self._collSolid.setPointB(0, self._getCollPointY(), 0)

    def _resetWheel(self):
        if not self.isActive():
            return

        self.camOffset = self._defaultOffset
        self._collSolid.setPointB(0, self._getCollPointY(), 0)
        self.setZ(self._defaultZ)

    def _getCollPointY(self):
        return self.camOffset[1] - 1

    def _startCollisionCheck(self):
        self._collSolid = CollisionSegment(0, 0, 0, 0, self._getCollPointY(), 0)
        collSolidNode = CollisionNode('FPSCam.CollSolid')
        collSolidNode.addSolid(self._collSolid)
        collSolidNode.setFromCollideMask(OTPGlobals.CameraBitmask | OTPGlobals.CameraTransparentBitmask | OTPGlobals.FloorBitmask)
        collSolidNode.setIntoCollideMask(BitMask32.allOff())
        self._collSolidNp = self.attachNewNode(collSolidNode)
        self._cHandlerQueue = CollisionHandlerQueue()
        self._cTrav = CollisionTraverser('FPSCam.cTrav')
        self._cTrav.addCollider(self._collSolidNp, self._cHandlerQueue)
        taskMgr.add(self._collisionCheckTask, FPSCamera.CollisionCheckTaskName, priority=45)

    def _collisionCheckTask(self, task=None):
        if hasattr(base, 'oobeMode') and base.oobeMode:
            return Task.cont

        self._cTrav.traverse(render)
        try:
            self._cHandlerQueue.sortEntries()
        except AssertionError:
            return Task.cont

        cNormal = (0, -1, 0)
        collEntry = None
        for i in xrange(self._cHandlerQueue.getNumEntries()):
            collEntry = self._cHandlerQueue.getEntry(i)
            cNormal = collEntry.getSurfaceNormal(self)
            if cNormal[1] < 0:
                break

        if not collEntry:
            if self.forceMaxDistance:
                camera.setPos(self.camOffset)
                camera.setZ(0)

            self.avatar.getGeomNode().show()
            return task.cont

        cPoint = collEntry.getSurfacePoint(self)
        offset = 0.9
        camera.setPos(cPoint + cNormal * offset)
        distance = camera.getDistance(self)
        if distance < 1.8:
            self.avatar.getGeomNode().hide()
        else:
            self.avatar.getGeomNode().show()

        localAvatar.ccPusherTrav.traverse(render)
        return Task.cont

    def _stopCollisionCheck(self):
        taskMgr.remove(FPSCamera.CollisionCheckTaskName)
        self._cTrav.removeCollider(self._collSolidNp)
        del self._cHandlerQueue
        del self._cTrav
        self._collSolidNp.detachNode()
        del self._collSolidNp
        self.avatar.getGeomNode().show()
