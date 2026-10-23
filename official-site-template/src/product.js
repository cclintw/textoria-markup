// To reuse: change this file, guide.json and public/assets/reader-preview.png.
export const product = {
  name: 'Textoria Markup', kind: 'CODEX SKILL',
  eyebrow: 'TEXTORIA MARKUP · CODEX SKILL',
  headline: ['把文本，', '變成可核對的知識。'],
  description: '詞表與規則負責比對，閱讀介面協助核對，對話完成修訂。',
  primaryAction: '安裝 Skill', secondaryAction: '查看示範',
  actionUrl: null, // Set a verified download/store/app URL to use a direct CTA instead of the installation dialog.
  image: '/assets/reader-preview.png',
  imageAlt: 'Textoria Markup 閱讀介面示意：左側實體清單、中央標註正文、右側實體資訊與 KWIC。',
  imageCaption: '介面示意 · 文本標註與實體核對',
  repository: 'https://github.com/cclintw/textoria-markup', license: 'GPL-3.0-or-later',
  install: {
    title: '把 Textoria Markup 帶進你的專案。',
    description: '在 Codex 專案對話中，透過 skill-installer 安裝；完成後，上傳正文並說明你的標註需求。',
    notice: '目前為本機專案預覽。以下 GitHub 安裝指令須待來源儲存庫發布後才能使用。',
    command: '$skill-installer --repo cclintw/textoria-markup --path .agents/skills/textoria-markup --dest .agents/skills',
    requirements: '需要 Codex、Python 3.10+ 及專案宣告的依賴。安裝 skill 本身不會建立使用者資料。',
  },
  steps: [
    { title: '準備文本', description: '匯入或貼上你的文本，確認章節，進入標註與核對流程。', icon: 'file' },
    { title: '提供詞表與規則', description: '設定人物、地點等詞表，或用對話描述比對條件。', icon: 'list' },
    { title: '核對與修訂', description: '在閱讀介面檢視標註，對照上下文，透過對話修訂。', icon: 'check' },
  ],
  topics: [
    { id: 'add', title: '新增實體', description: '選取原文，從一處標註開始。', icon: 'user' },
    { id: 'edit', title: '修改與清除', description: '精確修訂，保留原文與定位。', icon: 'pencil' },
    { id: 'keywords', title: '關鍵詞', description: '提供一行一詞的研究清單。', icon: 'search' },
    { id: 'vocabulary', title: '外部詞表', description: '整合正名、別名與實體類型。', icon: 'database' },
    { id: 'rules', title: '規則與詞夾子', description: '將前後文條件變成比對規則。', icon: 'sliders' },
    { id: 'export', title: '匯出與分享', description: '保留標註成果，繼續研究。', icon: 'export' },
  ],
  examples: [
    { id: 'vocabulary', title: '外部詞表', label: '名稱、類型與別名', source: '名稱,類型,別名\n曹操,人物,孟德\n劉備,人物,玄德\n孫權,人物,仲謀\n赤壁,地點,\n江東,地點,', prompt: '請依這份人物與地點詞表標註全文，保留不同類型；不要改動原文。', hits: ['曹操', '劉備', '孫權', '赤壁', '江東'] },
    { id: 'keywords', title: '關鍵詞清單', label: '每行一詞，不需要表頭', source: '結盟\n火攻\n東南風\n天下', prompt: '請依這份清單進行全書關鍵詞標註，使用預設 key-word 類型。', hits: ['結盟', '火攻', '東南風', '天下'] },
    { id: 'clipper', title: '詞夾子', label: '用前後文定義擷取範圍', source: '前文：名曰\n後文：，\n長度：2 到 6 字\n限制：不跨句號或段落\n類型：人物', prompt: '請擷取「名曰」到逗號間的二至六字，標為人物；只處理本段。', hits: ['周瑜'] },
  ],
  faq: [
    { question: '這是網站服務，還是安裝在 Codex 裡的工具？', answer: 'Textoria Markup 是 Codex skill。這個官網提供介紹、示範與使用指南；實際標註工作在你的專案內執行，產生本機閱讀網站與匯出檔。' },
    { question: '會自動讓 AI 再讀一次全文、提取實體嗎？', answer: '不會。預設由程式依你提供的詞表、關鍵詞或規則比對。只有你明確要求時，才透過獨立的實體提取 skill 準備參考詞表。' },
    { question: '支援哪些正文與詞表格式？', answer: '正文支援 TXT、Markdown、HTML／HTM，以及指定正文欄位的 CSV。詞表可使用名稱／類型／別名 CSV；關鍵詞可提供每行一詞的 TXT 或 Markdown。其他格式須先用合適工具讀取、轉換並核對。' },
    { question: '我的原文與標註資料存在哪裡？', answer: '原檔、工作檔與 corpus.json 主檔存放在專案的 textoria-markup/collections/ 下。網頁是衍生閱讀介面，不會自行回寫主檔。使用 Codex 及另行選用的服務時，仍依各服務的資料處理設定運作。' },
    { question: '可以把結果分享給其他人嗎？', answer: '可以要求匯出含全文與標註的單檔 HTML，或明確要求透過可用的 Sites 功能發布。發布是當次資料的快照，後續修訂須再次要求更新；訪客不會因此取得本機資料的編輯權限。' },
    { question: '有哪些目前需要注意的限制？', answer: '目前不支援任意交錯或巢狀標註，也尚未實作將新文件追加至既有 corpus。DocuXML 的實際建庫相容性須以 DocuSky 檢測及匯入結果為準。' },
  ],
};
