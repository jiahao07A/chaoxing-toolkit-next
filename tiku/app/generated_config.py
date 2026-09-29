"""Generated from config/settings.schema.json; do not edit manually."""

SCHEMA_VERSION = 1
SOURCE_SCHEMA_SHA256 = '9671e3860c8bfae650ca01178de22c61d7f9449d2b742cb69706b9c1bc6a27d4'
GENERATED_DEFAULTS = {'videoDiagnosticsEnabled': True, 'randomPauseEnabled': False, 'randomPauseIntervalMin': 30, 'randomPauseIntervalMax': 93, 'randomPauseDurationMin': 2, 'randomPauseDurationMax': 5}
GENERATED_RULES = {'videoDiagnosticsEnabled': {'type': 'boolean'}, 'randomPauseEnabled': {'type': 'boolean'}, 'randomPauseIntervalMin': {'type': 'integer', 'minimum': 1, 'maximum': 86400}, 'randomPauseIntervalMax': {'type': 'integer', 'minimum': 1, 'maximum': 86400}, 'randomPauseDurationMin': {'type': 'integer', 'minimum': 1, 'maximum': 3600}, 'randomPauseDurationMax': {'type': 'integer', 'minimum': 1, 'maximum': 3600}}
GENERATED_CONSTRAINTS = [['randomPauseIntervalMin', '<=', 'randomPauseIntervalMax'], ['randomPauseDurationMin', '<=', 'randomPauseDurationMax']]
