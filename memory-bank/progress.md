# Progress (Updated: 2026-04-15)

## Done

- 完成 0.4.3 release smoke：ruff、mypy、bandit、pytest、package_smoke、uv build、VSIX package 全部通過
- 補上 VSX gallery banner，並以 icon.svg 重產透明 icon.png，移除舊 PNG 的白色外框
- 將目前功能變更整理為可釋出的 0.4.3 版本：核心版號、extension 版號、uv.lock、CHANGELOG 已同步


## Doing

- 分段整理 git 變更並準備 commit / push / tag

## Next

- 檢查本機 VSCE / OVSX 憑證是否存在，能發佈就直接發佈，否則保留 tag 後走 GitHub Actions publish workflow
