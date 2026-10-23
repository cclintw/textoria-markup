# Textoria Markup 文本實體標註

[English](README.md) · [Codex Skill](.agents/skills/textoria-markup/SKILL.md) · [GPL v3 或後續版本授權](LICENSE)

Textoria Markup 是在 Codex 中使用的文本標註工具。您可以提供實體詞表、關鍵詞清單或標註規則，將文本整理成可依章節閱讀、查看實體與查找前後文的標註頁，並透過對話持續修訂。

如果還沒有詞表，也可以選擇由 AI 建立參考詞表，再套用到文本。完成後可保留在本機閱讀、匯出成果，或發布成網站供他人閱覽。

## 功能特色

- **多種標註來源**：使用既有詞表、關鍵詞清單、文字規則，或搭配 AI 提取的參考詞表；各種方式可以組合使用。
- **依章節閱讀**：保留文本的章節階層，在正文中以不同顏色呈現實體類型。
- **實體清單與前後文**：依類型瀏覽實體，查看出現段落及 KWIC（關鍵詞前後文），定位原文核對。
- **對話修訂**：複製頁面上的文字與位置資訊，請 Codex 新增、刪除或修改標註，可指定單次出現、段落、章節或全書。
- **詞表保存與重用**：保存修訂後的實體詞表，供後續標註工作參考。
- **成果匯出與分享**：提供單檔 HTML、DocuSky 詮釋資料表與 DocuXML，也可搭配 Sites 發布閱讀網站。

## 安裝

### 方法一：透過 Codex 安裝

在 Codex app 開啟您的工作專案，將下方指令貼到對話中送出：

```text
$skill-installer --repo cclintw/textoria-markup --path .agents/skills/textoria-markup --dest .agents/skills
```

安裝完成後，在下一回合開始使用。

### 方法二：手動下載安裝

1. 開啟 [GitHub 專案頁面](https://github.com/cclintw/textoria-markup)，選擇 **Code → Download ZIP**。
2. 解壓縮，找到 `.agents/skills/textoria-markup/` 資料夾；必要時開啟顯示隱藏檔案。
3. 將整個 `textoria-markup` Skill 資料夾複製到工作專案的 `.agents/skills/` 中。完成後，入口檔案的位置應為 `<工作專案>/.agents/skills/textoria-markup/SKILL.md`。

## 操作說明

### 1. 提供文本

在 Codex 專案中上傳文本，然後說：

```text
請針對上傳的文本進行標註。
```

支援 TXT、Markdown、HTML，以及指定正文欄位的 CSV。PDF 或圖片需先轉成文字，並核對辨識結果。也可以直接提供本機檔案路徑。

Codex 會確認文獻集的存放位置，保留原檔，並提供可核對的文本工作稿與章節預覽。您可以修改 Markdown 標題，或直接用對話描述章節安排；確認結構後即可進行標註。

### 2. 選擇標註來源

以下三種方式可單獨或組合使用：

| 方式 | 如何提供 |
|---|---|
| 實體詞表或關鍵詞清單 | 上傳名稱、類型、別名等資料，或一行一詞的關鍵詞清單。 |
| 標註規則 | 用文字描述要標註的條件，例如特定詞語之間的文字。 |
| AI 提取參考詞表 | 請 Codex 搭配 [Textoria Entity Extractor](https://github.com/cclintw/textoria-entity-extractor) 從文本建立詞表，再套用標註。 |

使用既有詞表時，可以說：

```text
請依上傳的詞表標註全文。
```

沒有詞表時，可以說：

```text
請由 AI 自動提取實體詞表，並完成全文標註。
```

AI 提取由 Textoria Entity Extractor 處理，Codex 會協助準備所需 Skill。未指定類型時，會涵蓋該工具支援的全部適用實體類型；您也可以依研究需要指定範圍。

以規則標註時，可以說：

```text
請將「名曰」之後、逗號之前的二至六字標為人物，不跨句號或段落。
```

### 3. 閱讀與修訂

完成後，開啟 Codex 提供的閱讀頁。左側可依類型瀏覽實體，中央閱讀正文，點選標註可查看實體資訊與出現段落。

需要修訂時，使用實體或段落旁的複製按鈕，將定位資訊貼回 Codex，再描述修改內容。例如：

```text
請將這一處的類型改為地名，只修改這次出現。
```

要新增標註，可先反白正文中的未標註文字，點選「＋」，再將複製的資訊貼回對話。頁面按鈕只複製資訊；送出修訂要求後，Codex 才會更新標註與閱讀頁。

### 4. 匯出與分享

您可以直接在對話中要求匯出，也可以點閱讀頁頂端的匯出圖示，將複製的指令貼回 Codex 送出。

| 成果 | 用途 |
|---|---|
| 實體詞表 CSV／JSON | 查看或重用標註詞表。JSON 可保留較完整的詞表與修訂資訊。 |
| 單檔 HTML | 在瀏覽器閱讀或分享完整標註文本，保留章節導覽、實體清單與前後文查找功能。 |
| DocuSky 詮釋資料 CSV／Excel | 整理標題、作者、年代與來源等資料，搭配 DocuXML 使用。 |
| DocuXML | 將文本與標註帶入 DocuSky 建庫流程。 |

實體詞表與 DocuSky 詮釋資料表用途不同；後者不是供批次標記使用的實體名稱清單。

需要網站連結時，可點地球圖示複製發布指令，再貼回 Codex 送出；此功能需要可用的 Sites。新網站預設為私人，發布內容包含全文與標註。之後若修訂文本，需再次發布才能更新線上版本。

## 成果保存與使用注意

成果存放在工作專案的 `textoria-markup/collections/` 下，各文獻集分別保存原檔、工作稿、標註資料、閱讀頁與匯出檔案。閱讀頁可以直接在本機瀏覽器開啟。

- 正式標註資料建立後，修改先前的 Markdown 工作稿不會自動更新標註；請透過 Codex 提出後續修訂。
- AI 詞表與文字比對可能有漏項或誤標，請依原文語境核對。部分重疊名稱無法同時顯示；目前不支援任意巢狀或交錯標註。
- 目前不支援將新文件追加至已建立的文獻集。新文本可另建文獻集處理。

## 版本與更新

更新資訊請參閱 [GitHub 專案頁面](https://github.com/cclintw/textoria-markup)。引用成果或記錄研究方法時，建議一併記下使用的版本或 Git 提交編號，以便日後核對。

## 作者與引用

作者與開發者：**Chance Chun-Cheng Lin**（GitHub：[cclintw](https://github.com/cclintw)）。引用本專案時，可使用以下格式，並補上使用版本：

```text
Chance Chun-Cheng Lin. Textoria Markup: A Codex Skill for Text Annotation. https://github.com/cclintw/textoria-markup.
```

軟體引用資料見 [CITATION.cff](CITATION.cff)，來源與致謝見 [NOTICE.md](NOTICE.md)。

## 授權

本專案採用 [GNU GPL 第 3 版或任何後續版本](LICENSE)（`GPL-3.0-or-later`）。來源文本與第三方素材的權利仍屬各自權利人。

## 支持專案

如果本專案對您的工作有幫助，歡迎給一顆 **GitHub 星星 ⭐**，或透過 Issue 回報問題與提出建議。分享文本案例前，請先確認素材的使用權限。
