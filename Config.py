# Configuration for Utils.py
RAW_DATA_PATH = 'Data/RawData/'
PREPROCESSED_DATA_PATH = 'Data/PreprocessedData/'
RAW_DATA_CSV_HEADER = ['Timestamp', 'Confidence', 'Diameter', 'Event']

# Configuration for ReadRawPupilData.py
EVENT_DEFAULT = 'default'
EVENT_SITTING = 'sitting'
EVENT_WALKING = 'walking'
EVENT_READING_SITTING = 'reading-sitting'
EVENT_READING_WALKING = 'reading-walking'

KEY_SITTING = 's'
KEY_WALKING = 'w'
KEY_READING_SITTING = 'r'
KEY_READING_WALKING = 'g'

# Configuration for main.py
# Mobile and reading
WALK_SIMPATH = 'walk_simpath'
WALK_STAIRPATH = 'walk_stairpath'
STAND = 'stand'

HARD = 'hard'
EASY = 'easy'
NOREAD = 'noread'

# N-BACK audio: https://dualn-back.com/
NOBACK = 'nothing'
ONEBACK ='ONEBACK'
TWOBACK = 'TWOBACK'
THREEBACK = 'THREEBACK'

# Luminance condition
LOWLUX = 'lowlux'
MIDDLELUX = 'middlelux'
HIGHLUX = 'highlux'

