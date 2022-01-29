from panda3d.core import *
from toontown.coghq import DistributedHealBarrelAI
from toontown.coghq import DistributedGagBarrelAI
from toontown.toonbase.ToontownBattleGlobals import AvPropDamage, THROW_TRACK

PieToonup = (3, 2, 1)
PieDamageMult = 1.0
AttackMult = (0.8, 1.0, 1.6)
AttackMultNerfed = 0.5
HitCountDamage = (350, 375, 375)
HitCountDamageNerfed = 175

SellbotBossMaxDamage = [1000, 1250, 1500]
SellbotBossMaxDamageNerfed = 500
SellbotBossBattleOnePosHpr = (0, -35, 0, -90, 0, 0)
SellbotBossBattleTwoPosHpr = (0, 60, 18, -90, 0, 0)
SellbotBossBattleThreeHpr = (180, 0, 0)
SellbotBossBottomPos = (0, -110, -6.5)
SellbotBossDeathPos = (0, -175, -6.5)
SellbotBossDooberTurnPosA = (-20, -50, 0)
SellbotBossDooberTurnPosB = (20, -50, 0)
SellbotBossDooberTurnPosDown = (0, -50, 0)
SellbotBossDooberFlyPos = (0, -135, -6.5)
SellbotBossTopRampPosA = (-80, -35, 18)
SellbotBossTopRampTurnPosA = (-80, 10, 18)
SellbotBossP3PosA = (-50, 40, 18)
SellbotBossTopRampPosB = (80, -35, 18)
SellbotBossTopRampTurnPosB = (80, 10, 18)
SellbotBossP3PosB = (50, 60, 18)


def getPieDamage(tier, toon=None):
    if toon:
        level = toon.pieType
    else:
        level = getPieLevel(tier)
    return AvPropDamage[THROW_TRACK][level][0][1]


def getPieLevel(tier):
    return 4 - tier


StrafeGearSizes = (0.15, 0.2, 0.25)
StrafeGearCount = (0.7, 1.0, 2.0)
StrafeGearTime = (1.8, 1.0, 0.8)
StrafeSpreadAngles = (50, 60, 65)

BarrelDefs = {8000: {'type': DistributedHealBarrelAI.DistributedHealBarrelAI,
        'pos': Point3(15, 23, 0),
        'hpr': Vec3(-45, 0, 0),
        'rewardPerGrab': 50,
        'rewardPerGrabMax': 0},
 8001: {'type': DistributedGagBarrelAI.DistributedGagBarrelAI,
        'pos': Point3(15, -23, 0),
        'hpr': Vec3(-135, 0, 0),
        'gagLevel': 3,
        'gagLevelMax': 0,
        'gagTrack': 3,
        'rewardPerGrab': 10,
        'rewardPerGrabMax': 0},
 8002: {'type': DistributedGagBarrelAI.DistributedGagBarrelAI,
        'pos': Point3(21, 20, 0),
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


BarrelsStartPos = (0, -36, -8)
BarrelsFinalPos = (0, -36, 0)
