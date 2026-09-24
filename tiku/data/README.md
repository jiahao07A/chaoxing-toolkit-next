# 运行数据目录

- `tiku.json` 是可提交的题库种子数据。
- `questions.db`、`config.json` 和日志属于本机运行时文件，已由根目录 `.gitignore` 排除。
- 可以通过 `TIKU_DATA_DIR` 指定整套运行数据目录，也可以通过 `DATABASE_FILE`、`JSON_FILE`、`CONFIG_FILE` 分别指定文件路径。

服务端会兼容整理前位于 `tiku/` 根目录的旧数据库和配置，避免升级时丢失本地数据。
