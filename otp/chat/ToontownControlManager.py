from direct.controls.ControlManager import ControlManager
from direct.showbase.InputStateGlobal import inputState
# from DirectGui import *
# from PythonUtil import *
# from IntervalGlobal import *

# from otp.avatar import Avatar
from direct.directnotify import DirectNotifyGlobal
# import GhostWalker
# import GravityWalker
# import NonPhysicsWalker
# import PhysicsWalker
# if __debug__:
#    import DevWalker
from direct.task import Task
from panda3d.core import ConfigVariableBool

# This is a hack, it may be better to use a line instead of a ray.
from toontown.toonbase import ToontownGlobals

CollisionHandlerRayStart = 4000.0


class ToontownControlManager(ControlManager):
    notify = DirectNotifyGlobal.directNotify.newCategory("ControlManager")
    wantWASD = base.wantCustomControls

    def __init__(self, enable=True, passMessagesThrough=False):
        self.istWASD = []
        self.istNormal = []
        self.fullTurning = False
        ControlManager.__init__(self, enable, passMessagesThrough)

    def enable(self):
        assert self.notify.debugCall(id(self))
        if not hasattr(self, '__WASDTurn'):
            self.__WASDTurn = True

        if self.isEnabled:
            assert self.notify.debug('already isEnabled')
            return

        self.isEnabled = 1

        # keep track of what we do on the inputState so we can undo it later on
        #self.inputStateTokens = []
        self.inputStateTokens.extend((
            inputState.watch('run', 'runningEvent', 'running-on', 'running-off'),
            inputState.watch('forward', 'force-forward', 'force-forward-stop'),
        ))

        if self.wantWASD:
            keymap = base.settings.settings.get('keymap', {})
            self.istWASD.extend((
                inputState.watch('turnLeft', 'mouse-look_left', 'mouse-look_left-done'),
                inputState.watch('turnLeft', 'force-turnLeft', 'force-turnLeft-stop'),
                inputState.watch('turnRight', 'mouse-look_right', 'mouse-look_right-done'),
                inputState.watch('turnRight', 'force-turnRight', 'force-turnRight-stop'),
                inputState.watchWithModifiers('forward', keymap.get('MOVE_UP', base.MOVE_UP),
                                              inputSource=inputState.WASD),
                inputState.watchWithModifiers('reverse', keymap.get('MOVE_DOWN', base.MOVE_DOWN),
                                              inputSource=inputState.WASD),
                inputState.watchWithModifiers('jump', keymap.get('JUMP', base.JUMP))
            ))

            self.setWASDTurn(self.getWASDTurn())
        else:
            self.istNormal.extend((
                inputState.watch('turnLeft', 'mouse-look_left', 'mouse-look_left-done'),
                inputState.watch('turnLeft', 'force-turnLeft', 'force-turnLeft-stop'),
                inputState.watch('turnRight', 'mouse-look_right', 'mouse-look_right-done'),
                inputState.watch('turnRight', 'force-turnRight', 'force-turnRight-stop'),
                inputState.watchWithModifiers('forward', base.MOVE_UP, inputSource=inputState.ArrowKeys),
                inputState.watchWithModifiers('reverse', base.MOVE_DOWN, inputSource=inputState.ArrowKeys),
                inputState.watchWithModifiers('turnLeft', base.MOVE_LEFT, inputSource=inputState.ArrowKeys),
                inputState.watchWithModifiers('turnRight', base.MOVE_RIGHT, inputSource=inputState.ArrowKeys),
                inputState.watch('jump', base.JUMP, base.JUMP + '-up')
            ))

        if self.currentControls:
            self.currentControls.enableAvatarControls()

    def disable(self):
        self.isEnabled = 0

        for token in self.istNormal:
            token.release()
        self.istNormal = []

        for token in self.inputStateTokens:
            token.release()
        self.inputStateTokens = []

        for token in self.istWASD:
            token.release()
        self.istWASD = []

        for token in self.WASDTurnTokens:
            token.release()
        self.WASDTurnTokens = []

        if self.currentControls:
            self.currentControls.disableAvatarControls()

        keymap = base.settings.settings.get('keymap', {})
        if self.passMessagesThrough:
            if self.wantWASD:
                self.istWASD.append(inputState.watchWithModifiers(
                    'forward', keymap.get('MOVE_UP', base.MOVE_UP), inputSource=inputState.WASD))
                self.istWASD.append(inputState.watchWithModifiers(
                    'reverse', keymap.get('MOVE_DOWN', base.MOVE_DOWN), inputSource=inputState.WASD))
                self.istWASD.append(inputState.watchWithModifiers(
                    'turnLeft', keymap.get('MOVE_LEFT', base.MOVE_LEFT), inputSource=inputState.WASD))
                self.istWASD.append(inputState.watchWithModifiers(
                    'turnRight', keymap.get('MOVE_RIGHT', base.MOVE_RIGHT), inputSource=inputState.WASD))
            else:
                self.istNormal.append(
                    inputState.watchWithModifiers(
                        'forward',
                        base.MOVE_UP,
                        inputSource=inputState.ArrowKeys))
                self.istNormal.append(
                    inputState.watchWithModifiers(
                        'reverse',
                        base.MOVE_DOWN,
                        inputSource=inputState.ArrowKeys))
                self.istNormal.append(
                    inputState.watchWithModifiers(
                        'turnLeft',
                        base.MOVE_LEFT,
                        inputSource=inputState.ArrowKeys))
                self.istNormal.append(
                    inputState.watchWithModifiers(
                        'turnRight',
                        base.MOVE_RIGHT,
                        inputSource=inputState.ArrowKeys))

    def setWASDTurn(self, turn):
        self.__WASDTurn = turn

        if not self.isEnabled:
            return

        turnLeftWASDSet = inputState.isSet("turnLeft", inputSource=inputState.WASD)
        turnRightWASDSet = inputState.isSet("turnRight", inputSource=inputState.WASD)
        slideLeftWASDSet = inputState.isSet("slideLeft", inputSource=inputState.WASD)
        slideRightWASDSet = inputState.isSet("slideRight", inputSource=inputState.WASD)

        for token in self.WASDTurnTokens:
            token.release()

        if turn:
            self.WASDTurnTokens = (
                inputState.watchWithModifiers("turnLeft", base.MOVE_LEFT, inputSource=inputState.WASD),
                inputState.watchWithModifiers("turnRight", base.MOVE_RIGHT, inputSource=inputState.WASD),
                )

            inputState.set("turnLeft", slideLeftWASDSet, inputSource=inputState.WASD)
            inputState.set("turnRight", slideRightWASDSet, inputSource=inputState.WASD)

            inputState.set("slideLeft", False, inputSource=inputState.WASD)
            inputState.set("slideRight", False, inputSource=inputState.WASD)

        else:
            self.WASDTurnTokens = (
                inputState.watchWithModifiers("slideLeft", base.MOVE_LEFT, inputSource=inputState.WASD),
                inputState.watchWithModifiers("slideRight", base.MOVE_RIGHT, inputSource=inputState.WASD),
                )

            inputState.set("slideLeft", turnLeftWASDSet, inputSource=inputState.WASD)
            inputState.set("slideRight", turnRightWASDSet, inputSource=inputState.WASD)

            inputState.set("turnLeft", False, inputSource=inputState.WASD)
            inputState.set("turnRight", False, inputSource=inputState.WASD)

    def getWASDTurn(self):
        return self.__WASDTurn
