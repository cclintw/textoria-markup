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

1. 上傳正文，自動檢查編碼並確認文獻集歸屬，立即複製原檔到 uploads/。TXT、Markdown、HTML、指定正文欄位的 CSV 有來源處理程式；PDF／圖片等須先以適當工具轉換並核對。
2. 清理／格式準備結果一律存為 UTF-8 的 clean/原名_clean.md，附準備報告，並在右側開啟。使用者可編輯 #、##、### 標題，或以對話指定結構；Codex 讀取最新版、列出章節與分段預覽，確認後才建立 corpus.json 與固定 ID。
3. 上傳實體對照表、一行一詞的關鍵詞清單，或混合自然語言規則。詞表、規則與 AI 提取可以合併使用。明確選擇 AI 提取後，先查找 Textoria Entity Extractor skill；未安裝時依指定的 GitHub 來源使用 skill-installer 安裝，再按其啟用流程接續處理。新輸入的詞表與提取結果合併整理後再標註。
4. Codex 判讀附件，整理為統一詞表與結構化規則。只在欄位或語意不明時詢問；確認範圍後直接標註。新來源的多類型衝突全部保留。
5. 程式更新 `corpus.json`，重新產生網站與正式詞表。
6. 使用者看原文，點實體或反白未標註文字，再點複製／新增圖示，貼到 Codex 下達修訂指令。每次新增、修改、清除均先確認作用範圍。

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
└── textoria-markup/collections/collection-文本代號/
    ├── uploads/
    ├── clean/                    # UTF-8 Markdown 工作檔與準備報告
    ├── corpus.json               # 結構確認後才建立
    ├── site/
    ├── exports/{entity.json,entity.csv}
    └── .history/                 # 有修改時按需保存的壓縮版本
```

`corpus.json` 是唯一正式主檔，保存正文、章節、段落、類型、實體、別名、規則、標註、輸入紀錄與排除條件。結構確認前保留原檔及可編輯的 clean Markdown；其餘清理與解析過程使用系統暫存，不再永久產生三份中間檔、AI 提取快取或候選詞表。corpus 建立後，修改 clean 檔不會自動改寫正式正文或標註。

每次成功標註或修訂後更新正式詞表：JSON 保留完整資料供重用；CSV 供閱讀與交換，按別名及類型分列，保留 ID 和範圍。下次重標優先沿用正式詞表及人工修訂，與新來源的差異記錄在 corpus。曾清除的標註不因重跑自動復活。

## 前端與匯出

網頁模板、header/footer、左右側欄及正文 parts 共用同一套；內容從 corpus 填入，CSS/JS 複製到 site。工作前端是 HTML，不直接寫入主檔；Codex 修改後重建並重新整理。支援 file:// 閱讀、全書 KWIC、三種定位複製、選取新增與同頁籤說明返回。

基本詞夾子、正則、排除及範圍條件已有共用引擎；自然語言由 Codex 轉為 JSON，不執行上傳的任意 Python。部分重疊留作可定位的未套用紀錄，目前不支援任意巢狀／交錯標記。

匯出選項為單檔 HTML、CSV／Excel 詮釋資料表、DocuXML。單檔 HTML 包含左右欄、章節切換與 KWIC 定位，CSS／JS 全部內嵌；DocuXML 預設以第一層章節為一件，完整保留下層段落與標註。

Python 需求見 [requirements.txt](requirements.txt)，Codex 優先沿用可用 runtime，安裝新環境或依賴前取得授權。開發者測試：

```sh
python -m unittest discover -s .agents/skills/textoria-markup/scripts/tests -v
```

專案以 GPL-3.0-or-later 授權，作者資訊見 [CITATION.cff](CITATION.cff)，來源說明見 [NOTICE.md](NOTICE.md)。正文、網站、匯出、暫存與備份預設不提交 Git。既有《紅樓夢》原版 UI 留在本機忽略的備份目錄，供重構比較與回復。


### 匯出

「＋」右側依序為 HTML、CSV／Excel、DocuXML 圖示。按圖示複製指令，貼到 Codex 後執行，輸出放在 exports/：

- 文獻集名稱.html：完整閱讀介面，左右欄、章節選單與定位功能保留；CSS、JS、全文資料內嵌，移除頂端標註與匯出工具。
- 文獻集名稱_metadata.csv／.xlsx：同一份可編輯詮釋資料，第一層章節一列，filename 與 DocuXML 對應。表格不包含全文，方便使用 DocuSky 詮釋資料整合工具補充標題、作者、年代與來源。
- 文獻集名稱_docu.xml：直接交給 DocuSky 的建庫格式；第一層章節為一件，包含全部下層段落及最新標註，另保留完整章節樹與標註編號。已做原文及結構檢查，實際建庫相容性仍須以 DocuSky 檢測／匯入結果為準。

CSV／Excel 匯出使用可用的 spreadsheet runtime；HTML、DocuXML 不需要 spreadsheet runtime。舊 TEI 檔案保留原狀，不列為目前匯出選項。
