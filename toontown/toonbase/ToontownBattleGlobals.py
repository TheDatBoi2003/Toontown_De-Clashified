from ToontownGlobals import *
import math
import TTLocalizer

# ToontownBattle globals: central repository for all battle globals

# defaults for camera

BattleCamFaceOffFov = 30.0
BattleCamFaceOffPos = Point3(0, -10, 4)

# BattleCamDefaultPos = Point3(0, -10, 11)
# BattleCamDefaultHpr = Vec3(0, -45, 0)
BattleCamDefaultPos = Point3(0, -8.6, 16.5)
BattleCamDefaultHpr = Vec3(0, -61, 0)
BattleCamDefaultFov = 80.0
BattleCamMenuFov = 65.0
BattleCamJoinPos = Point3(0, -12, 13)
BattleCamJoinHpr = Vec3(0, -45, 0)

MAX_TOON_CAPACITY = 4

# This might be set true by a magic word to skip over the playback movie.
SkipMovie = 0

# avatar start hp
BaseHp = 15

# avatar track names and numbers
Tracks = TTLocalizer.BattleGlobalTracks
NPCTracks = TTLocalizer.BattleGlobalNPCTracks

TrackColors = ((211 / 255.0, 148 / 255.0, 255 / 255.0),
               (249 / 255.0, 93 / 255.0, 93 / 255.0),
               (79 / 255.0, 190 / 255.0, 76 / 255.0),
               (93 / 255.0, 108 / 255.0, 239 / 255.0),
               (255 / 255.0, 65 / 255.0, 199 / 255.0),
               (249 / 255.0, 255 / 255.0, 93 / 255.0),
               (255 / 255.0, 145 / 255.0, 66 / 255.0),
               (67 / 255.0, 243 / 255.0, 255 / 255.0),
               )

# try:
#    wantAllProps = base.config.GetBool('want-all-props', 0)
# except:
#    wantAllProps = simbase.config.GetBool('want-all-props', 0)
# if (wantAllProps == 1):
#    for i in range(len(TrackZones)):
#        TrackZones[i] = ToontownCentral

HEAL_TRACK = 0
TRAP_TRACK = 1
LURE_TRACK = 2
SOUND_TRACK = 3
SQUIRT_TRACK = 4
ZAP_TRACK = 5
THROW_TRACK = 6
DROP_TRACK = 7

MIN_TRACK_INDEX = 0
MAX_TRACK_INDEX = 7

# Special NPC Toon actions
NPC_RESTOCK_GAGS = MAX_TRACK_INDEX + 1
NPC_TOONS_HIT = MAX_TRACK_INDEX + 2
NPC_COGS_MISS = MAX_TRACK_INDEX + 3

MIN_LEVEL_INDEX = 0
MAX_LEVEL_INDEX = 7

ACC_UP_TRACKS = [DROP_TRACK]

OPERA_LEVEL_INDEX = MAX_LEVEL_INDEX

RAILROAD_LEVEL_INDEX = MAX_LEVEL_INDEX + 1

ANVIL_LEVEL_INDEX = 3

SHIP_LEVEL_INDEX = MAX_LEVEL_INDEX + 1

WEDDING_LEVEL_INDEX = MAX_LEVEL_INDEX

# Track icons used for various UI
TrackIcons = [1, 5, 2, 1, 4, 0, 4, 3]

# which props buffs which track
PropTypeToTrackBonus = {
    AnimPropTypes.Hydrant: SQUIRT_TRACK,
    AnimPropTypes.Mailbox: THROW_TRACK,
    AnimPropTypes.Trashcan: HEAL_TRACK,
}

# avatar skill levels (totalled)
Levels = [0, 20, 100, 500, 2000, 6000, 10000, 15000]
# The first 2 are from a "balanced" gag progression suggestion I wrote up a while ago,
# the last one is simply one to remove the game's grind. ~ DTM1218
# Levels = [0, 20, 100, 500, 1700, 4200, 8500, 14000] # Suggestion 1
# Levels = [0, 20, 100, 500, 2000, 5000, 10000, 17500] # Suggestion 2
# Levels = [0, 5, 50, 200, 500, 1000, 1800, 3000] # Anti-Grind

# MaxSkill = 10000 # Original
MaxSkill = 20000
# MaxSkill = 5000 # Anti-Grind
# This is the maximum amount of experience per track that may be
# earned in one battle (or in one building).
ExperienceCap = 1500

# This accuracy (a percentage) is the highest that can ever be attained.
MaxToonAcc = 95

# avatar starting skill level
StartingLevel = 0

CarryLimits = ((10, 0, 0, 0, 0, 0, 0, 0),  # lvl 1
               (10, 5, 0, 0, 0, 0, 0, 0),  # lvl 2
               (15, 10, 5, 0, 0, 0, 0, 0),  # lvl 3
               (20, 15, 10, 5, 0, 0, 0, 0),  # lvl 4
               (25, 20, 15, 10, 3, 0, 0, 0),  # lvl 5
               (30, 25, 20, 15, 7, 3, 0, 0),  # lvl 6
               (30, 25, 20, 15, 7, 3, 2, 0),  # lvl 7
               (30, 25, 20, 15, 7, 3, 2, 1))  # lvl 8


# avatar prop maxes
MaxProps = ((20, 40), (30, 60), (80, 100))

# death-list flag masks for BattleExperience
DLF_SKELECOG = 0x01
DLF_FOREMAN = 0x02
DLF_SUPERVISOR = 0x04
DLF_CLERK = 0x08
DLF_PRESIDENT = 0x10
DLF_BOSS = 0x20
DLF_VIRTUAL = 0x40
DLF_REVIVES = 0x80

# Pie names.  These map to props in BattleProps, but it must be
# defined here beccause BattleProps cannot be included on the AI.
pieNames = ['tart',
            'fruitpie-slice',
            'creampie-slice',
            'cake-slice',
            'fruitpie',
            'creampie',
            'birthday-cake',
            'wedding-cake',
            'water-balloon',
            'lawbook',  # used in battle three of lawbot boss
            ]

# avatar prop icon filenames
AvProps = (('feather', 'bullhorn', 'lipstick', 'bamboocane',
            'pixiedust', 'baton', 'pixiedust', 'baton'),
           ('banana', 'rake', 'quicksand', 'marbles',
            'quicksand', 'trapdoor', 'wreckingball', 'tnt', 'traintrack'),
           ('1dollar', 'smmagnet', '5dollar', 'bigmagnet',
            '10dollar', 'hypnogogs', '50dollar', 'hypnogogs'),
           ('bikehorn', 'bikehorn', 'whistle', 'bugle',
            'aoogah', 'elephant', 'foghorn', 'singing'),
           ('cupcake', 'fruitpieslice', 'creampieslice', 'creampieslice',
            'fruitpie', 'creampie', 'cake', 'cake'),
           ('flower', 'waterglass', 'waterballoon', 'waterballoon',
            'bottle', 'firehose', 'stormcloud', 'stormcloud'),
           ('flower', 'waterglass', 'waterballoon', 'waterballoon',
            'bottle', 'firehose', 'stormcloud', 'stormcloud'),
           ('flowerpot', 'sandbag', 'sandbag', 'anvil',
            'weight', 'safe', 'piano', 'piano'))

AvPropsNew = (
    ('inventory_feather', 'inventory_megaphone', 'inventory_lipstick', 'inventory_bamboo_cane',
     'inventory_pixiedust', 'inventory_juggling_cubes', 'inventory_cannon', 'inventory_ladder'),
    ('inventory_banana_peel', 'inventory_rake', 'inventory_springboard', 'inventory_marbles',
     'inventory_quicksand_icon', 'inventory_trapdoor', 'inventory_wreckingball', 'inventory_tnt'),
    ('inventory_1dollarbill', 'inventory_small_magnet', 'inventory_5dollarbill', 'inventory_big_magnet',
     'inventory_10dollarbill', 'inventory_hypno_goggles', 'inventory_50dollarbill', 'inventory_screen'),
    ('inventory_kazoo', 'inventory_bikehorn', 'inventory_whistle', 'inventory_bugle',
     'inventory_aoogah', 'inventory_elephant', 'inventory_fog_horn', 'inventory_opera_singer'),
    ('inventory_squirt_flower', 'inventory_glass_of_water', 'inventory_water_gun', 'inventory_waterballoon',
     'inventory_seltzer_bottle', 'inventory_firehose', 'inventory_storm_cloud', 'inventory_geyser'),
    ('inventory_joybuzzer', 'inventory_carpet', 'inventory_balloon', 'inventory_battery',
     'inventory_tazer', 'inventory_television', 'inventory_tesla', 'inventory_lightning'),
    ('inventory_cup_cake', 'inventory_fruit_pie_slice', 'inventory_cream_pie_slice', 'inventory_cake_slice',
     'inventory_fruitpie', 'inventory_creampie', 'inventory_cake', 'inventory_wedding'),
    ('inventory_flower_pot', 'inventory_sandbag', 'inventory_bowlingball', 'inventory_anvil',
     'inventory_weight', 'inventory_safe_box', 'inventory_boulder', 'inventory_piano')
)

# prettier on-screen versions of the prop names
AvPropStrings = TTLocalizer.BattleGlobalAvPropStrings

# prettier on-screen versions of the prop names for singular usage
AvPropStringsSingular = TTLocalizer.BattleGlobalAvPropStringsSingular

# prettier on-screen versions of the prop names for plural usage
AvPropStringsPlural = TTLocalizer.BattleGlobalAvPropStringsPlural

# avatar prop accuracies
AvPropAccuracy = ((95, 95, 95, 95, 95, 95, 95, 95),  # Heal
                  (0, 0, 0, 0, 0, 0, 0, 0, 0),  # Trap (always hits)
                  (65, 65, 70, 70, 75, 75, 80, 80),  # Lure
                  (95, 95, 95, 95, 95, 95, 95, 95),  # Sound
                  (95, 95, 95, 95, 95, 95, 95, 95),  # Squirt
                  (30, 30, 30, 30, 30, 30, 30, 30),  # Zap
                  (75, 75, 75, 75, 75, 75, 75, 75),  # Throw
                  (50, 50, 50, 50, 50, 50, 50, 50, 95)  # Drop
                  )
AvBonusAccuracy = ((95, 95, 95, 95, 95, 95, 95, 95),  # Heal
                   (0, 0, 0, 0, 0, 0, 0, 0, 0),  # Trap (always hits)
                   (70, 70, 75, 75, 80, 80, 85, 95),  # Lure
                   (95, 95, 95, 95, 95, 95, 95, 95),  # Sound
                   (95, 95, 95, 95, 95, 95, 95, 95),  # Squirt
                   (30, 30, 30, 30, 30, 30, 30, 30),  # Zap
                   (75, 75, 75, 75, 75, 75, 75, 75),  # Throw
                   (65, 65, 65, 65, 65, 65, 65, 65, 95))  # Drop

AvLureRounds = (2, 2, 3, 3, 4, 4, 5, 5)
AvSoakRounds = (1, 1, 2, 2, 3, 3, 4, 4)

AvZapJumps = ((3, 2.25, 1.5),
              (3, 2.5, 2),
              (3, 2.75, 2.5))

AvTrackAccStrings = TTLocalizer.BattleGlobalAvTrackAccStrings

# avatar prop damages
# each entry represents a toon prop track and is a list of pairs,
# the first of each pair represents the damage range (min to max) which
# maps to the second pair which represents the toon's track
# exp.  So the higher the toon's exp in that prop's track, the more damage
# that particular prop can do
#
AvPropDamage = (
    # Heal
    (((6, 8), (Levels[0], Levels[1])),  # tickle
     ((12, 15), (Levels[1], Levels[2])),  # group Joke
     ((22, 26), (Levels[2], Levels[3])),  # kiss
     ((33, 39), (Levels[3], Levels[4])),  # group Dance
     ((45, 50), (Levels[4], Levels[5])),  # dust
     ((63, 78), (Levels[5], Levels[6])),  # group Juggle
     ((85, 95), (Levels[6], Levels[7])),  # cannon
     ((105, 135), (Levels[7], MaxSkill))),  # group Dive
    # Trap
    (((18, 20), (Levels[0], Levels[1])),
     ((27, 35), (Levels[1], Levels[2])),
     ((42, 50), (Levels[2], Levels[3])),
     ((65, 75), (Levels[3], Levels[4])),
     ((90, 115), (Levels[4], Levels[5])),
     ((130, 160), (Levels[5], Levels[6])),
     ((180, 220), (Levels[6], Levels[7])),
     ((235, 280), (Levels[7], MaxSkill)),
     ((280, 280), (-1, -1))),
    # Lure
    (((0, 0), (0, 0)),
     ((0, 0), (0, 0)),
     ((0, 0), (0, 0)),
     ((0, 0), (0, 0)),
     ((0, 0), (0, 0)),
     ((0, 0), (0, 0)),
     ((0, 0), (0, 0)),
     ((0, 0), (0, 0))),
    # Sound
    (((3, 4), (Levels[0], Levels[1])),
     ((5, 7), (Levels[1], Levels[2])),
     ((9, 11), (Levels[2], Levels[3])),
     ((14, 16), (Levels[3], Levels[4])),
     ((19, 21), (Levels[4], Levels[5])),
     ((26, 32), (Levels[5], Levels[6])),
     ((35, 50), (Levels[6], Levels[7])),
     ((55, 65), (Levels[7], MaxSkill))),
    # Squirt
    (((3, 4), (Levels[0], Levels[1])),
     ((6, 8), (Levels[1], Levels[2])),
     ((10, 12), (Levels[2], Levels[3])),
     ((18, 21), (Levels[3], Levels[4])),
     ((27, 30), (Levels[4], Levels[5])),
     ((45, 56), (Levels[5], Levels[6])),
     ((60, 80), (Levels[6], Levels[7])),
     ((90, 115), (Levels[7], MaxSkill))),
    # Zap
    (((3, 4), (Levels[0], Levels[1])),
     ((5, 6), (Levels[1], Levels[2])),
     ((8, 10), (Levels[2], Levels[3])),
     ((14, 16), (Levels[3], Levels[4])),
     ((21, 24), (Levels[4], Levels[5])),
     ((35, 40), (Levels[5], Levels[6])),
     ((50, 66), (Levels[6], Levels[7])),
     ((70, 80), (Levels[7], MaxSkill))),
    # Throw
    (((6, 8), (Levels[0], Levels[1])),
     ((10, 13), (Levels[1], Levels[2])),
     ((18, 21), (Levels[2], Levels[3])),
     ((30, 35), (Levels[3], Levels[4])),
     ((45, 50), (Levels[4], Levels[5])),
     ((65, 90), (Levels[5], Levels[6])),
     ((100, 130), (Levels[6], Levels[7])),
     ((140, 170), (Levels[7], MaxSkill))),
    # Drop
    (((10, 12), (Levels[0], Levels[1])),
     ((18, 20), (Levels[1], Levels[2])),
     ((30, 35), (Levels[2], Levels[3])),
     ((45, 55), (Levels[3], Levels[4])),
     ((65, 80), (Levels[4], Levels[5])),
     ((90, 125), (Levels[5], Levels[6])),
     ((145, 180), (Levels[6], Levels[7])),
     ((200, 220), (Levels[7], MaxSkill)),
     ((220, 220), (-1, -1))),
)

TRAP_EXE_BONUS = 0.3
TRAP_HEALTH_BONUS = 0.2

# avatar prop target type (0 for single target,
# 1 for group target)
# AvPropTargetCat is a grouping of target types
# for a single track and AvPropTarget is which
# target type group from AvPropTargetCat each
# toon attack track uses
#
ATK_SINGLE_TARGET = 0
ATK_GROUP_TARGET = 1
AvPropTargetCat = ((ATK_SINGLE_TARGET,
                    ATK_GROUP_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_GROUP_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_GROUP_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_GROUP_TARGET),
                   (ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET),
                   (ATK_GROUP_TARGET,
                    ATK_GROUP_TARGET,
                    ATK_GROUP_TARGET,
                    ATK_GROUP_TARGET,
                    ATK_GROUP_TARGET,
                    ATK_GROUP_TARGET,
                    ATK_GROUP_TARGET,
                    ATK_GROUP_TARGET),
                   (ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_SINGLE_TARGET,
                    ATK_GROUP_TARGET),
                   )

AvPropTarget = (0, 1, 0, 2, 1, 1, 1, 1)


def getTrapDamage(trapLevel, toon, suit=None, execBonus=0, healthBonus=0):
    if suit:
        execBonus = suit.isExecutive
        healthBonus = toon.checkTrackPrestige(TRAP_TRACK) and suit.currHP >= suit.maxHP / 2
    damage = getAvPropDamage(TRAP_TRACK, trapLevel, toon.experience.getExp(TRAP_TRACK))
    if healthBonus:
        damage += math.ceil(damage * TRAP_HEALTH_BONUS)
    if execBonus:
        damage += math.ceil(damage * TRAP_EXE_BONUS)
    return int(damage)


def getAvPropDamage(attackTrack, attackLevel, exp):
    """
    ////////////////////////////////////////////////////////////////////
    // Function:   get the appropriate prop damage based on various
    //             attributes of the prop and the toon
    // Parameters: attackTrack, the track of the prop
    //             attackLevel, the level of the prop
    //             exp, the toon's exp in the specified track
    // Changes:
    ////////////////////////////////////////////////////////////////////
    """
    # Map a damage value for the prop based on the track exp of the
    # toon, for example, a throw might have 3-6 damage which maps
    # to 0-30 exp.  So at 0 to 7.75 exp, the throw will do 3 damage;
    # at 7.75 to 15.5 exp, the throw will do 4 damage; at 15.5 to 23.25,
    # the throw will do 5 damage; at 23.25 to 30 exp, the throw will
    # do 6 damage;  at more than 30 exp, the throw will max out at 6
    # damage
    #
    minD = AvPropDamage[attackTrack][attackLevel][0][0]
    maxD = AvPropDamage[attackTrack][attackLevel][0][1]
    minE = AvPropDamage[attackTrack][attackLevel][1][0]
    maxE = AvPropDamage[attackTrack][attackLevel][1][1]
    expVal = min(exp, maxE)
    expPerHp = float((maxE - minE) + 1) / float((maxD - minD) + 1)
    damage = math.floor((expVal - minE) / expPerHp) + minD
    # In the gag purchase tutorial the sneak peak gags show as negative
    if damage <= 0:
        damage = minD
    return damage


# def isGroup(track, level):
#    if ((track == SOUND_TRACK) or
#        (((track == HEAL_TRACK) or (track == LURE_TRACK)) and
#         ((level == 1) or (level == 3) or (level == 5) or (level == 7)))):
#        return 1
#    else:
#        return 0

def isGroup(track, level):
    return AvPropTargetCat[AvPropTarget[track]][level]


def getCreditMultiplier(floorIndex):
    """
    Returns the skill credit multiplier appropriate for a particular
    floor in a building battle.  The floorIndex is 0 for the first
    floor, up through 4 for the top floor of a five-story building.
    """
    # Currently, this is 1 for the first floor (floor 0), 1.5 for the
    # second floor (floor 1), etc.
    return 1 + floorIndex * 0.5 * 2


def getFactoryCreditMultiplier(factoryId):
    """
    Returns the skill credit multiplier for a particular factory.
    factoryId is the factory-interior zone defined in ToontownGlobals.py.
    """
    # for now, there's only one factory
    return 2.


def getFactoryMeritMultiplier(factoryId):
    """
    Returns the skill merit multiplier for a particular factory.
    factoryId is the factory-interior zone defined in ToontownGlobals.py.
    """
    # Many people complained about how many runs you must make now that 
    # we lowered the cog levels so I have upped this by a factor of two.
    return 4.


def getMintCreditMultiplier(mintId):
    """
    Returns the skill credit multiplier for a particular mint.
    mintId is the mint-interior zone defined in ToontownGlobals.py.
    """
    return {CashbotMintIntA: 4., CashbotMintIntB: 5, CashbotMintIntC: 6.}.get(mintId, 1)


def getStageCreditMultiplier(stageId):
    """
    Returns the skill credit multiplier for a particular mint.
    stageId is the stage-interior zone defined in ToontownGlobals.py.
    """
    return {LawbotStageIntA: 4., LawbotStageIntB: 5., LawbotStageIntC: 6., LawbotStageIntD: 7.,}.get(stageId, 1.)


def getCountryClubCreditMultiplier(countryClubId):
    """
    Returns the skill credit multiplier for a particular mint.
    mintId is the mint-interior zone defined in ToontownGlobals.py.
    """
    return {
        BossbotCountryClubIntA: 4.,
        BossbotCountryClubIntB: 5.,
        BossbotCountryClubIntC: 6.,
    }.get(countryClubId, 1.)


def getBossBattleCreditMultiplier(battleNumber):
    """
    Returns the skill credit multiplier for the two first battles of
    the final battle sequence with the Senior V.P.  battleNumber is 1
    for the first battle and 2 for the second battle.
    """
    return 1 + battleNumber


def getInvasionMultiplier():
    """
    Returns the skill credit multiplier during invasions.
    This gets multiplied on every street battle and in every interior.
    User must first check to see if there is an invasion.
    """
    return 2.0


def getMoreXpHolidayMultiplier():
    """
    Returns the skill credit multiplier during the more xp holiday.
    This gets multiplied on every street battle and in every interior.
    User must first check to see if there is an invasion.
    """
    return 2.0


def encodeUber(trackList):
    bitField = 0
    for trackIndex in range(len(trackList)):
        if trackList[trackIndex] > 0:
            bitField += pow(2, trackIndex)
    return bitField


def decodeUber(flagMask):
    if flagMask == 0:
        return []
    maxPower = 16
    workNumber = flagMask
    workPower = maxPower
    trackList = []
    # print("build")
    # while (workNumber > 0) and (workPower >= 0):
    while (workPower >= 0):
        if workNumber >= pow(2, workPower):
            workNumber -= pow(2, workPower)
            trackList.insert(0, 1)
        else:
            trackList.insert(0, 0)
        # print("Number %s List %s" % (workNumber, trackList))
        workPower -= 1
    endList = len(trackList)
    foundOne = 0
    # print("compress")
    while not foundOne:
        # print trackList
        if trackList[endList - 1] == 0:
            trackList.pop(endList - 1)
            endList -= 1
        else:
            foundOne = 1
    return trackList


def getUberFlag(flagMask, index):
    decode = decodeUber(flagMask)
    if index >= len(decode):
        return 0
    else:
        return decode[index]


def getUberFlagSafe(flagMask, index):
    if (flagMask == "unknown") or (flagMask < 0):
        return -1
    else:
        return getUberFlag(flagMask, index)
