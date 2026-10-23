// Import trusted, authored help content. No user input or remote HTML is loaded.
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = process.argv[2] ? path.resolve(process.argv[2]) : path.resolve(root, '../.agents/skills/textoria-markup/themes/default/static/help.html');
const html = readFileSync(source, 'utf8');
const sections = [...html.matchAll(/<section id="([a-z-]+)">([\s\S]*?)<\/section>/g)].map(([, id, body]) => {
  body = body.replace(/<span class="tag">[\s\S]*?<\/span>/g, '');
  const heading = body.match(/<h2>([\s\S]*?)<\/h2>/);
  if (!heading) throw new Error(`Missing heading: ${id}`);
  let title = heading[1].replace(/<[^>]+>/g, '').trim();
  if (id === 'publish') {
    title = '發布標註成果';
    body = body.replace(/<h2>[\s\S]*?<\/h2>/, `<h2>${title}</h2>`);
  }
  if (id === 'start') body = body.replace(/<p class="note">[\s\S]*?<\/p>/, '<p class="note">以下說明適用於安裝後產生的標註閱讀介面。複製與新增按鈕位於該介面內；本官網提供操作指南與示範，不會直接修改你的專案資料。</p>');
  return { id, title, html: body };
});
if (!sections.length || new Set(sections.map(s => s.id)).size !== sections.length) throw new Error('Missing or duplicate guide sections');
writeFileSync(path.join(root, 'src/guide.json'), JSON.stringify(sections, null, 2) + '\n');
console.log(`Imported ${sections.length} guide sections from ${source}`);
