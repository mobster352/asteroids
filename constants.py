# SCREEN_WIDTH = 1920
# SCREEN_HEIGHT = 1080

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

ASTEROID_MIN_RADIUS = 20
ASTEROID_KINDS = 3
ASTEROID_SPAWN_RATE = 0.8  # seconds
ASTEROID_MAX_RADIUS = ASTEROID_MIN_RADIUS * ASTEROID_KINDS

PLAYER_RADIUS = 20
PLAYER_TURN_SPEED = 300
PLAYER_SPEED = 200
PLAYER_SHOOT_SPEED = 500
PLAYER_SHOOT_COOLDOWN = 0.3

SHOT_RADIUS = 5

BACKGROUND_IMAGE = "images/space3.jpg"
SAVE_FILE = "data/data.pickle"
FONT_FILE = "fonts/Rogbold-3llGM.otf"

LASER_SOUND_FILE = "sounds/laser1.ogg"
EXPLOSION_L_SOUND_FILE = "sounds/explosion3.ogg"
EXPLOSION_S_SOUND_FILE = "sounds/explosion2.ogg"
ENGINE_SOUND_FILE = "sounds/engine1.wav"
SHIP_EXPLOSION = "sounds/explosion6.ogg"

ENABLE_SOUNDS = False

HOST = '0.0.0.0'
CLIENT_HOST = '192.168.0.100'
#'0.0.0.0' # Accept any LAN
#'192.168.0.100' # Windows LAN IP
#'172.30.75.51' # WSL LAN IP
#'127.0.0.1' # Localhost
PORT = 65432

PING_ACTION = 0
GET_ACTION = 1
DESTROY_ACTION = 2

IN_MENU = 0
IN_SINGLEPLAYER_GAME = 1
IN_MULTIPLAYER_MENU = 2
IN_CREATE_ROOM_MENU = 3
IN_JOIN_ROOM_MENU = 4
IN_MULTIPLAYER_GAME = 5

MAX_CONNECTIONS = 2

# is_server_alive (bool)
PING_STRUCT = '!?'
# header type (uint), (unsigned char)
MSG_HEADER = '!IB'  # 4-byte length (excluding length field), 1-byte type
# action (unsigned_char)
ACTION_STRUCT = '!B'  # Network byte order
# client_id (unsigned_char), is_connected (bool)
CLIENT_STRUCT = '!B?'
# player_position_x (float32), player_position_y (float32), player_rotation (f)
PLAYER_STRUCT = '!fff'
# asteroid_id (uint32), position_x (float32), position_y (float32), radius (ushort16) 
ASTEROID_STRUCT = '!IffH'
# shot_id (uint32), position_x (float32), position_y (float32), radius (ushort16), used (bool)
SHOT_STRUCT = '!IffH?'
# num_connections (unsigned char)
SERVER_DATA_STRUCT = '!B'
# destroy_asteroid_id (uint32)
DESTROY_ASTEROID_STRUCT = '!I'

MSG_TYPE_PING = 0
MSG_TYPE_ACTION = 1
MSG_TYPE_CLIENT = 2
MSG_TYPE_PLAYER = 3
MSG_TYPE_ASTEROID = 4
MSG_TYPE_SHOT = 5
MSG_TYPE_SERVER_DATA = 6
MSG_TYPE_DESTROY_ASTEROID = 7

TCP_PORT = 65432