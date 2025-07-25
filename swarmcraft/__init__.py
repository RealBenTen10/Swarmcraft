from enum import Enum


class CARDINAL_DIRS(Enum):
    NORTH = (1, 0, 0)
    EAST = (0, 0, 1)
    SOUTH = (-1, 0, 0)
    WEST = (0, 0, -1)
    UP = (0, 1, 0)
    DOWN = (0, -1, 0)
    NE = (0.707, 0, 0.707)
    NW = (0.707, 0, -0.707)
    SE = (-0.707, 0, 0.707)
    SW = (-0.707, 0, -0.707)

class BLOCK_TYPES(Enum):
    DIAMOND = 'diamond_block'
    GOLD = 'gold_block'
    EMERALD = 'emerald_block'
    WHITE_WOOL = 'white_wool'
    BLACK_WOOL = 'black_wool'
    RED_WOOL = 'red_wool'
    ORANGE_WOOL = 'orange_wool'
    YELLOW_WOOL = 'yellow_wool'
    GREEN_WOOL = 'green_wool'
    BLUE_WOOL = 'blue_wool'
    PURPLE_WOOL = 'purple_wool'
    BROWN_WOOL = 'brown_wool'
    GRASS = 'grass_block'
    BEDROCK = 'bedrock'
    AIR = 'air'

class MOVEMENT_KEYS(Enum):
    FORWARD = 'forward'
    BACKWARD = 'back'
    LEFT = 'left'
    RIGHT = 'right'
    JUMP = 'jump'
    SPRINT = 'sprint'
    SNEAK = 'sneak'
