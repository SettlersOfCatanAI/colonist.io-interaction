import numpy as np

# conversion arrays for colonist to jsettlers
TILE_TYPES = [6, 5, 1, 3, 4, 2]
PORT_TYPES = [0, 5, 1, 3, 4, 2]

# coords of the middle of the 0th hex in each row
ZERO_COORDS = {-3: [543, 176], -2: [583, 244], -1: [623, 312], 0: [662, 380], 1: [702, 448], 2: [742, 516], 3: [782, 584]}

# coords of top left corner of player interfaces
PLAYER_COORDS = [[1108, 27], [1108, 373], [4, 373]]

# coords in relation to top left corner of player interface
SIT_HERE = np.array([126, 163])
START = np.array([144, 29])
QUIT = np.array([28, 331])

# coords of absolute buttons
QUIT_SURE = [758, 434]
NAME_BOX = [80, 50]
NEW_GAME = [780, 75]
JOIN_GAME = [780, 95]