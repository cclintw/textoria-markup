# Textoria Markup 文本實體標註

[English](README.md)

以 Codex 對話整理外部詞表、關鍵詞、詞夾子與規則，再由程式比對正文、產生標註網站。使用者閱讀原文與 KWIC，複製定位資訊後，透過對話修訂。**不再預設讓 AI 全文提取一次實體，也不設候選詞表審核關卡。**

## 安裝

待 GitHub 儲存庫發布至 `cclintw/textoria-markup` 後，在 Codex 專案對話中貼上：

```text
$skill-installer --repo cclintw/textoria-markup --path .agents/skills/textoria-markup --dest .agents/skills
```

本次僅準備本機專案，未建立遠端儲存庫、推送或發布。安裝只放入 skill，首次實際處理才建立使用者資料；安裝器尚不提供自動更新既有安裝的功能。本專案沒有建立 Codex 外掛。

## 使用流程

1. 上傳正文。支援 TXT、Markdown、HTML／HTM、指定正文欄位的 CSV；PDF／圖片等須先以適當工具轉換並核對。單純上傳檔案或討論工具，不會開始標註。
2. Codex 自動檢查編碼與可讀性，先確認文獻集歸屬，再將原檔逐位元組複製到 `uploads/`。清理／格式準備結果一律存為 UTF-8 的 `clean/原名_clean.md`，附準備報告及可點擊連結；只有使用者要求時才在面板或瀏覽器開啟。有實質影響的清理先確認，不覆寫已編輯的工作檔。只要求清理時，到此結束，不建立 corpus 或網站。
3. 建立結構時，使用者可編輯 Markdown 標題（`# 卷一`、`## 城內`、`### 永寧寺`，# 後加空格），或以對話指定結構。Codex 重讀最新版，列出章節順序與分段預覽，確認後才建立 `corpus.json` 與固定 ID。建立後再次提供實際儲存的章節階層供核對，確認後才進行標註；每次結構修訂也須重新預覽。
4. 上傳實體對照表、一行一詞的關鍵詞清單，或描述標註規則，也可明確選擇由 AI 提取參考詞表。選擇 AI 提取後，先查找 Textoria Entity Extractor skill；未安裝時依指定來源使用 skill-installer 安裝，再按其啟用流程接續處理。Codex 將新詞表、規則與提取結果合併整理後再標註；Markup 本身不再做第二次全文實體提取，缺少詞表也不會自動觸發提取。新來源的多類型與明確身分衝突全部保留，既有正式詞表及人工修訂優先。
5. 確認操作與作用範圍後，程式直接比對、更新 `corpus.json`，重新產生網站與正式詞表。使用者已明確指定操作及範圍時，即可沿用該授權。
6. 使用者看原文，點實體或反白未標註文字，再點複製／新增圖示，貼到 Codex 下達修訂指令。圖示只複製定位資訊，不儲存或傳送訊息。每次新增、修改、清除均先確認操作及單次／段落／章節／全書範圍，不因選取一處就推定全書修改。

目前尚未實作將新文件追加至既有 corpus；不可為了追加正文或修改標註，從原始檔重建或取代既有主檔。階段界線與目前限制見 [workflow](.agents/skills/textoria-markup/references/workflow.md)。

對話範例：

```text
請保留原文標點，依上傳詞表標註全書；不同類型全部保留。

請將這份一欄式清單作為關鍵詞標註，預設類型 key-word。

上傳檔案同時包含人物名單和詞夾子，請整理後直接標註。
詞夾子擷取「名曰」到逗號之間二至六字，標為人物，不跨句號或段落。
```

## 檔案架構

```text
<PROJECT>/
├── .agents/skills/textoria-markup/
│   ├── SKILL.md
│   ├── agents/
│   ├── assets/
│   ├── references/
│   ├── scripts/
│   └── themes/default/
│       ├── templates/parts/
│       └── static/{css,js}/
└── textoria-markup/collections/collection-<ASCII-slug>/
    ├── uploads/
    ├── clean/                    # UTF-8 Markdown 工作檔與準備報告
    ├── corpus.json               # 結構確認後才建立
    ├── site/
    ├── exports/{entity.json,entity.csv}
    └── .history/                 # 有修改時按需保存的壓縮版本
```

`corpus.json` 是唯一正式主檔，保存正文、章節、段落、類型、實體、別名、規則、標註、輸入紀錄與排除條件。結構確認前保留原檔及可編輯的 clean Markdown；其餘清理與解析過程使用系統暫存，不再永久產生三份中間檔、AI 提取快取或候選詞表。corpus 建立後，修改 clean 檔不會自動改寫正式正文或標註。

建立結構或重建未標註網站不會產生 `exports/`。套用標註輸入或修訂後更新正式詞表，包括已接受但沒有命中的詞；明確要求匯出時也可產生詞表。JSON 保留完整詞表與身分關聯供重用；CSV 供閱讀與交換，按別名及類型分列，保留 ID 和範圍。下次重標優先沿用正式詞表及人工修訂，與新來源的差異記錄在 corpus。清除標註仍保留實體主檔及範圍排除條件，不因重跑自動復活。

## 前端與匯出

網頁模板、header/footer、左右側欄及正文 parts 共用同一套；內容從 corpus 填入，CSS/JS 複製到 site。工作前端是 HTML，不直接寫入主檔；Codex 修改後重建並重新整理。支援 file:// 閱讀、全書 KWIC、三種定位複製、選取新增與同頁籤說明返回。

章節選單呈現實際階層；沒有自有段落的章節保留標題，顯示通往第一個可讀子章節的路徑，並保留段落所屬章節與固定 ID。若主檔已儲存但網站產生失敗，須回報主檔已更新、閱讀介面仍舊，重建成功後才能宣告網站已更新。

基本詞夾子、正則、排除及範圍條件已有共用引擎；自然語言由 Codex 轉為 JSON，不執行上傳的任意 Python。部分重疊留作可定位的未套用紀錄，目前不支援任意巢狀／交錯標記。

不自動進行社會網絡／共現分析、翻譯或語意提取；網站發布須另有明確的 Sites 發布請求。

### 匯出

「＋」右側依序為 HTML、CSV／Excel、DocuXML 圖示。按圖示複製指令，明確提交匯出請求後由 Codex 執行，輸出放在 `exports/`：

- `文獻集名稱.html`：完整閱讀介面，左右欄、階層章節選單與檔內 KWIC 定位功能保留；CSS、JS、全文資料內嵌，移除頂端新增、匯出及說明工具。
- `文獻集名稱_metadata.csv`／`.xlsx`：同一份可編輯詮釋資料，第一層章節一列，filename 與 DocuXML 對應。表格不包含全文，也不是 BatchTagging 指令表，供 DocuSky 詮釋資料整合工具補充標題、作者、年代與來源。
- `文獻集名稱_docu.xml`：DocuXML 1.3 建庫格式；第一層章節為一件，包含全部下層段落及最新標註，另以自訂詮釋資料保留完整章節樹與標註來源資訊。本機檢查涵蓋原文、結構及詞法相容性，實際建庫相容性仍須以 DocuSky 檢測／匯入結果為準。

CSV／Excel 匯出在需要時解析可用的內附 spreadsheet runtime，不會默默安裝依賴；HTML、DocuXML 不需要 spreadsheet runtime。舊 TEI 檔案保留原狀；TEI、EPUB、SQLite、Access 不列入目前匯出選單。詳見 [匯出說明](.agents/skills/textoria-markup/references/exports.md)。

## Sites 發布

DocuXML 右側的地球圖示只複製文獻集專屬發布指令，點擊本身不代表授權發布。明確提交發布請求後，使用可用的 Sites skill／工具；新建網站預設為私人，更新已指定的既有網站時保留其身分與閱覽權限。

發布以最新單檔閱讀介面作為靜態首頁，包含全文與標註；不包含 uploads、clean、corpus 主檔、歷史版本或無關檔案。展示版保留頂端圖示作為只複製指令的控制項，並將完整說明另存為同頁籤開啟的頁面。初次載入與切換章節時收合所有實體類別；從說明返回時可恢復閱讀狀態。這些控制項不授予編輯權限。

發布是當時資料的快照，不會隨 corpus 修改自動同步。Codex 回傳已核實的部署網址；若 Sites 不可用，則提供本機單檔閱讀介面，不自動改用其他代管平台。

## 開發

Python 需求見 [requirements.txt](requirements.txt)，Codex 優先沿用可用 runtime，安裝新環境或依賴前取得授權。開發者測試：

```sh
python -m unittest discover -s .agents/skills/textoria-markup/scripts/tests -v
```

專案以 GPL-3.0-or-later 授權，作者資訊見 [CITATION.cff](CITATION.cff)，來源說明見 [NOTICE.md](NOTICE.md)。正文、網站、匯出、暫存與備份預設不提交 Git。既有《紅樓夢》原版 UI 留在本機忽略的備份目錄，供重構比較與回復。
