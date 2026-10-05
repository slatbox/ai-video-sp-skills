# ai-video-sp-skills

Minis (OpenMinis) AI 视频生成 skill 套件，统一在此做版本管理。

本仓库部署位置为 `/var/minis/shared/ai-video-sp-skills/`，各 skill 通过软链接接入
`/var/minis/skills/`，Minis 会照常识别。

## 包含的 skill

| skill | 说明 |
|---|---|
| ai-video-superpowers-brainstorm | 阶段一：访谈收集需求 → spec.md |
| ai-video-superpowers-spec-to-plan | 阶段二：spec → plan.md（≤15s SEG 切分+校验） |
| zhike-image | 智核 TT Image 2.5 图片生成（文生图/图生图/编辑） |
| zhike-video | 智核海螺 H3 视频生成 |

> ai-video-superpowers-plan-to-video（阶段三执行）暂未纳入本仓库，仍在 /var/minis/skills/ 本地。

## 同步到 Minis 的方式

```sh
for s in zhike-image zhike-video ai-video-superpowers-brainstorm ai-video-superpowers-spec-to-plan; do
  ln -sfn /var/minis/shared/ai-video-sp-skills/$s /var/minis/skills/$s
done
```

注意：API key 不在仓库内（zhike key 存于 /var/minis/shared/zhike/）。
