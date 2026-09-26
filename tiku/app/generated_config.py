"""Generated from config/settings.schema.json; do not edit manually."""

SCHEMA_VERSION = 1
SOURCE_SCHEMA_SHA256 = '317199fbf6671a2b737b0e885771f928db0c6df5b1f8ad3293eb600aad77eb36'
GENERATED_DEFAULTS = {'videoDiagnosticsEnabled': True, 'randomPauseEnabled': True, 'randomPauseIntervalMin': 30, 'randomPauseIntervalMax': 93, 'randomPauseDurationMin': 2, 'randomPauseDurationMax': 5}
GENERATED_RULES = {'videoDiagnosticsEnabled': {'type': 'boolean'}, 'randomPauseEnabled': {'type': 'boolean'}, 'randomPauseIntervalMin': {'type': 'integer', 'minimum': 1, 'maximum': 86400}, 'randomPauseIntervalMax': {'type': 'integer', 'minimum': 1, 'maximum': 86400}, 'randomPauseDurationMin': {'type': 'integer', 'minimum': 1, 'maximum': 3600}, 'randomPauseDurationMax': {'type': 'integer', 'minimum': 1, 'maximum': 3600}}
GENERATED_CONSTRAINTS = [['randomPauseIntervalMin', '<=', 'randomPauseIntervalMax'], ['randomPauseDurationMin', '<=', 'randomPauseDurationMax']]
