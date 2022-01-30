from direct.showbase.MessengerGlobal import messenger
from pandac.PandaModules import *
from direct.showbase.InputStateGlobal import inputState
from direct.directnotify import DirectNotifyGlobal
from direct.showbase.PythonUtil import reduceAngle, fitSrcAngle2Dest, clamp
from direct.task import Task
from otp.otpbase import OTPGlobals
from otp.otpbase.PythonUtil import ParamObj
from toontown.camera import CameraMode
from toontown.toonbase import ToontownGlobals

NUM_ZOOMS = 23
INIT_DIST = 3.0
DEFAULT_Z = 2.5
INC_RATE = 1. / 3.

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
        self._getDefaultOffsets()
        self.camOffset = self._defaultOffset
        self._lastZoomLevel = self._defaultDistance
        self._firstPerson = False
        self._lastFov = None
        if params is None:
            self.setDefaultParams()
        else:
            params.applyTo(self)

        self.zIval = None
        self.camIval = None
        self.forceMaxDistance = True
        self.avFacingScreen = False

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
        self.camOffset.setY(self._lastZoomLevel)
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
        base.camLens.setMinFov(ToontownGlobals.DefaultCameraFov / (4. / 3.))
        base.camLens.setFov(ToontownGlobals.DefaultCameraFov)
        self._zoomToDistance(self._lastZoomLevel)
        self._startCollisionCheck()

    def exitActive(self):
        if self.camIval:
            self.camIval.finish()
            self.camIval = None

        self._lastZoomLevel = self.camOffset.getY()
        self.ignore('wheel_up')
        self.ignore('wheel_down')
        self._resetWheel()
        self._stopCollisionCheck()
        base.camNode.setLodCenter(NodePath())

        CameraMode.CameraMode.exitActive(self)

    def _getDefaultOffsets(self):
        try:
            self._defaultZ = base.localAvatar.getClampedAvatarHeight()
        except:
            self._defaultZ = DEFAULT_Z
        self._defaultDistance = -INIT_DIST * self._defaultZ
        self._minDistance = -self._defaultZ
        self._zoomIncrement = self._defaultZ * INC_RATE
        self._maxDistance = self._minDistance - self._zoomIncrement * NUM_ZOOMS
        self._defaultOffset = Vec3(0, self._defaultDistance, self._defaultZ)

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
        if self._firstPerson:
            return
        yDist = self.camOffset[1] + self._zoomIncrement
        self._zoomToDistance(yDist)

    def _handleWheelDown(self):
        if self._firstPerson:
            self._exitFPSMode()
        yDist = self.camOffset[1] - self._zoomIncrement
        self._zoomToDistance(yDist)

    def _zoomToDistance(self, yDist):
        if yDist >= self.camOffset.getY() >= self._minDistance:
            self._beginFPSMode()
            y = 0
        else:
            y = clamp(yDist, self._minDistance, self._maxDistance)
        self.camOffset.setY(y)
        if hasattr(self, '_collSolid'):
            self._collSolid.setPointB(0, self._getCollPointY(), 0)

    def _beginFPSMode(self):
        self.enableMouseControl()
        self.ignore('mouse3')
        self.ignore('mouse3-up')
        self.accept('mouse3', self.clickSecondAction)
        self.accept('mouse3-up', self.clickSecondAction)
        self.MinP = -70
        self.MaxP = 40
        self._lastFov = base.localAvatar.fov
        self.avatar.setCameraFov(90.0)
        self._firstPerson = True

    def _exitFPSMode(self):
        self.disableMouseControl()
        self.ignore('mouse3')
        self.ignore('mouse3-up')
        self.accept('mouse3', self.enableMouseControl)
        self.accept('mouse3-up', self.disableMouseControl)
        self.MinP = -50
        self.MaxP = 20
        self.avatar.setCameraFov(self._lastFov)
        self._firstPerson = False

    def _resetWheel(self):
        if not self.isActive():
            return

        self.camOffset = self._defaultOffset
        self.notify.info('resetWheel: ' + str(self.camOffset))
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
        self.cTravOnFloor.traverse(render)
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
        elif collEntry.hasSurfacePoint():
            cPoint = collEntry.getSurfacePoint(self)
            offset = 0.9
            camera.setPos(cPoint + cNormal * offset)

        if not base.localAvatar.isDisguised:
            distance = camera.getDistance(self)
            if distance < self._zoomIncrement:
                self.avatar.getGeomNode().hide()
            else:
                self.avatar.getGeomNode().show()

        base.localAvatar.ccPusherTrav.traverse(render)
        return Task.cont

    def _stopCollisionCheck(self):
        taskMgr.remove(FPSCamera.CollisionCheckTaskName)
        self._cTrav.removeCollider(self._collSolidNp)
        del self._cHandlerQueue
        del self._cTrav
        self._collSolidNp.detachNode()
        del self._collSolidNp
        if not base.localAvatar.isDisguised:
            self.avatar.getGeomNode().show()

    def clickSecondAction(self):
        if self.camOffset.getY() == 0:
            messenger.send(base.SECOND_ACTION_BUTTON)
