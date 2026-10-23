# 產品官網通用範本

採用選定的第三個視覺方向：白底、藍色主按鈕、置中 Hero、大幅產品展示與主題式指南。這是可執行的一頁式網站，以 Textoria Markup 示範；沒有部署，也不會修改標註資料。

## 本機預覽

需要 Node.js 22.12+（或符合 Vite／React plugin 需求的 Node 20.19+）。

```sh
npm install
npm run dev -- --host 127.0.0.1 --port 4173
```

開啟終端機顯示的本機網址。正式建置使用 `npm run build`；靜態前端輸出在 `dist/client/`。伺服器、Sites 建置腳本與測試保留在專案內，日後要求發布時可接續使用。

## 套用到下一個產品

複製此目錄時排除 `node_modules/`、`dist/`、`.vite/`、`qa/`，再依下表替換：

| 檔案 | 替換內容 |
| --- | --- |
| `src/product.js` | 產品名稱、定位、主標題、CTA、安裝指令、流程、主題與 FAQ |
| `src/guide.json` | 使用指南，每個主題包含 `id`、`title`、`html` |
| `public/assets/reader-preview.png` | 真實截圖或明確標示的介面示意；並更新 `product.js` 的 alt、caption |
| `src/styles.css` | `--accent` 品牌色、字型、留白與版面 |
| `src/App.jsx` | 自訂互動示範；目前 Demo 是 Textoria 的三種標註範例 |
| `index.html` | 網頁標題、語言、description、theme-color |

`product.actionUrl` 預設為 `null`，主 CTA 開啟安裝說明。設為已核實的商店、下載或 App 網址，即改為直接前往該入口，適合 plugin／app／tool；skill 可維持安裝指令彈窗。安裝指令中的來源發布狀態也須核實後更新，不能只移除警語而保留不存在的入口。

`guide.json` 的 HTML 是可信作者內容，直接渲染在頁面中；勿放入未經處理的使用者上傳 HTML、script 或事件屬性。未知評價、下載數、價格與相容平台不預填。

## Textoria 操作說明來源

指南取自同一專案的 `.agents/skills/textoria-markup/themes/default/static/help.html`，保留十個主題及對話、詞表、規則與匯出範例。已移除本機頁面的返回導航，並補充「本官網不直接修改資料」的情境說明。

來源更新後，在這個目錄執行：

```sh
npm run sync:guide
# 或明確指定另一份可信的 help.html：
node scripts/sync-guide.mjs /absolute/path/to/help.html
```

這會重新產生 `src/guide.json`，不修改來源。其他產品可直接編輯 JSON，或另加自己的文件轉換流程。

## 行為與素材

- Hero 使用 AI 生成的介面示意，已標明用途，不是真實產品截圖；圖內控制項不互動。下方另有實際可操作的範例。
- 範例可切換外部詞表／關鍵詞／詞夾子，點標註查看 KWIC，並複製對話指令。
- 使用指南、FAQ、手機導覽與安裝彈窗可操作。只複製指令，不會執行安裝。
- 標註示範使用頁內固定文本，不讀取、上傳或修改 corpus。
- 字型為 Google Fonts 的 Noto Sans TC，連線不可用時使用系統中文字型。圖示為 Phosphor Icons。品牌與產品截圖可依下一個產品替換。

## 設計參考

研究於 2026-10-23：

- [Cap](https://cap.so/)：產品首屏、成果展示與 CTA。
- [Elementor](https://elementor.com/)：產品介紹、功能敘事與使用資源入口。
- [Skills](https://www.skills.sh/)：清楚的安裝路徑及文件入口。
- [Codex 社群市集](https://www.codex-marketplace.com/)：工具分類及工作流程；此站並非 OpenAI 官方網站。
- [OpenAI Developers plugin](https://developers.openai.com/learn/developers-codex-plugin)：外掛介紹、開始使用與文件的組織方式。
- [Phosphor Icons](https://phosphoricons.com/)：介面圖示。

這些是研究參考，未複製它們的程式、商標、宣傳數字或使用者評價。視覺基準為本次選定的第三張設計稿，保留於 `qa/reference.png`；檢查結果見 `design-qa.md`。
