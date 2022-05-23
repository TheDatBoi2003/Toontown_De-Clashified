from panda3d.core import *
from toontown.coghq import DistributedHealBarrelAI
from toontown.coghq import DistributedGagBarrelAI

BarrelDefs = {8000: {'type': DistributedHealBarrelAI.DistributedHealBarrelAI,
        'pos': Point3(-23, 142, 0.025),
        'hpr': Vec3(-45, 0, 0),
        'rewardPerGrab': 25,
        'rewardPerGrabMax': 0},
 8001: {'type': DistributedGagBarrelAI.DistributedGagBarrelAI,
        'pos': Point3(-55, 137, 0.025),
        'hpr': Vec3(-135, 0, 0),
        'gagLevel': 6,
        'gagLevelMax': 0,
        'gagTrack': 5,
        'rewardPerGrab': 10,
        'rewardPerGrabMax': 0},
 8002: {'type': DistributedGagBarrelAI.DistributedGagBarrelAI,
        'pos': Point3(43, 133, 0.025),
        'hpr': Vec3(-45, 0, 0),
        'gagLevel': 3,
        'gagLevelMax': 0,
        'gagTrack': 4,
        'rewardPerGrab': 10,
        'rewardPerGrabMax': 0},
 8003: {'type': DistributedGagBarrelAI.DistributedGagBarrelAI,
        'pos': Point3(21, -20, 0),
        'hpr': Vec3(-135, 0, 0),
        'gagLevel': 3,
        'gagLevelMax': 0,
        'gagTrack': 5,
        'rewardPerGrab': 10,
        'rewardPerGrabMax': 0}}


def setBarrelAttr(barrel, entId):
    for defAttr, defValue in BarrelDefs[entId].iteritems():
        setattr(barrel, defAttr, defValue)


BarrelsStartPos = (0, 0, 0)
BarrelsFinalPos = (0, 0, 0)
