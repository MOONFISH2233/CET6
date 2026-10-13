# 六级真题精读 + 备考打卡站

个人自用的大学英语六级备考站点。把 2022-06 ~ 2026-06 的 33 套真题（听力原文、阅读逐段翻译、
逐题解析、翻译参考译文、写作范文）整理成静态网页，配一套 69 天冲刺计划。

| 页面 | 路径 | 说明 |
|---|---|---|
| 精读站 | `/cet6/` | 按考期 / 按题型进任意一篇，做题 → 核实对错 → 精读 → 句子中背单词 |
| 打卡站 | `/cet6/plan/` | 61 天计划（2026-10-12 ~ 12-11，考试 12-12），今日任务 + 进度 |
| 我的学习 | `/cet6/me.html` | 生词本 / 错题本 / 句子收藏（存在浏览器 localStorage，不上传） |
| 重点词 | `/cet6/hfw.html` | 真题高频词总表，按 CEFR 等级筛选、搜索、一键收词 |
| 背单词 | `/cet6/review.html` | 弹英文、4 选 1 中文；词从生词本来，SM-2 排复习（`cet6:srs`） |

## 目录

```
build/
  fetch.py            抓懒笔记的解析页 -> raw/
  build_data.py       raw/ 的 HTML 解析成结构化 JSON -> data/paper/
  build_dict.py       汇总「真题高频词」-> data/dict.json（核心词库）+ data/hfw/
  build_dict_all.py   用 ECDICT 裁出兜底词库 -> data/dict_all.json
  build_quotes.py     解析 ../美工/*.md 的台词 -> data/quotes.json
  build_img.py        生成站点用图 -> site/assets/img/
  gen_site.py         生成精读站（首页 / 套卷页 / 模块页 / 专项页 / 我的学习 / 重点词 / 背单词）
  gen_plan.py         生成打卡站 -> site/plan/
  gen_pdf.py          生成 PDF（精读版 + 速查版）
  pipeline.py         一键全流程（--no-fetch 跳过抓取）
  _check_site.py      生成后自检
  _rv_test.js         背单词页功能实测（Playwright，390×780）
  _rv_design.js       新页面与既有页面的 computed style 逐项比对（防「加了东西设计变了」）
  _rv_edge.js         背单词页边界（空生词本 / 查不到释义 / SM-2 到期口径 / 发音已撤掉的回归）
  _rv_fold.js         生词本分组折叠 + 展开状态记忆
  _rv_live.js         部署后打线上地址复测
  data/               解析结果 + 词库 + 台词（进仓库）
  raw/                抓下来的原始 HTML（不进仓库，可用 fetch.py 重抓）
  _cache/             ECDICT 原始 csv 缓存（不进仓库）
  site/               生成好的静态站点（进仓库，可直接部署）
```

## 重建

```bash
python build_data.py       # 需要先有 raw/（用 python fetch.py 抓，或直接跑 pipeline.py）
python build_dict.py
python build_dict_all.py   # 首次需要下载 ECDICT 到 _cache/，脚本里写了镜像地址
python build_quotes.py
python build_img.py        # 需要 ../美工/ 里的原图
python gen_site.py
python gen_plan.py
python _check_site.py
```

## 部署

纯静态文件，`site/` 整个丢到任意静态目录即可（nginx、`python -m http.server` 都行）。
站点按 `assets/` 相对定位，放在子目录（如 `/cet6/`）也能正常工作。

线上是 `http://47.109.130.65:5173/cet6/`（阿里云 ECS，借 A 股学习站的静态目录）。
上传用 tar 流 + scp —— PowerShell 直接把 tar 管道给 ssh 会破坏二进制：

```powershell
cd site; tar -czf "$env:TEMP\cet6.tgz" .
scp -i ~/.ssh/astock-ed25519 "$env:TEMP\cet6.tgz" root@47.109.130.65:/tmp/
ssh -i ~/.ssh/astock-ed25519 root@47.109.130.65 "cd /opt/astock-learn/public/cet6 && tar -xzf /tmp/cet6.tgz"
```

传完用 `Invoke-WebRequest` 逐文件比对字节数（别只看「传上去了」），再用 `node _rv_live.js` 打线上复测。

## 数据来源与版权

- **真题与解析**抓自懒笔记（english-exam.lazynote.cn），版权归原权利人所有，**仅供个人学习、非商业使用**。
- **兜底词库**由 [ECDICT](https://github.com/skywind3000/ECDICT) 裁剪而来，MIT 许可，见 `THIRD_PARTY_LICENSES.md`。
- **台词与图片**（`../美工/`，仅本地）版权归原作者／版权方所有，站内声明为个人学习非商业使用。

> 备份仓库 `MOONFISH2233/CET6` 目前是**公开**的（用户知情后选的）。要再分发解析内容有版权风险，
> 想收回的话把它改回私有即可。
