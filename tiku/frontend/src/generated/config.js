// Generated from config/settings.schema.json; do not edit manually.
export const CONFIG_SCHEMA_VERSION = 1
export const SOURCE_SCHEMA_SHA256 = '317199fbf6671a2b737b0e885771f928db0c6df5b1f8ad3293eb600aad77eb36'
export const GENERATED_CONFIG_FIELDS = [
  {
    "key": "videoDiagnosticsEnabled",
    "type": "boolean",
    "default": true,
    "minimum": null,
    "maximum": null,
    "description": "是否在 Tampermonkey 本地记录脱敏视频诊断"
  },
  {
    "key": "randomPauseEnabled",
    "type": "boolean",
    "default": true,
    "minimum": null,
    "maximum": null,
    "description": "是否启用视频随机暂停"
  },
  {
    "key": "randomPauseIntervalMin",
    "type": "integer",
    "default": 30,
    "minimum": 1,
    "maximum": 86400,
    "description": "随机暂停触发间隔下限（秒）"
  },
  {
    "key": "randomPauseIntervalMax",
    "type": "integer",
    "default": 93,
    "minimum": 1,
    "maximum": 86400,
    "description": "随机暂停触发间隔上限（秒）"
  },
  {
    "key": "randomPauseDurationMin",
    "type": "integer",
    "default": 2,
    "minimum": 1,
    "maximum": 3600,
    "description": "随机暂停时长下限（秒）"
  },
  {
    "key": "randomPauseDurationMax",
    "type": "integer",
    "default": 5,
    "minimum": 1,
    "maximum": 3600,
    "description": "随机暂停时长上限（秒）"
  }
]
