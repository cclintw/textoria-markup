/* Translate existing Textoria spans into the reference reader's view contract.
   This file performs no writes and never calls an annotation/save endpoint. */
(() => {
  const singleFile=window.TEXTORIA_SINGLE_FILE||null;
  const fills={person:'#fff0b8',place:'#dff3e6',office:'#d9e9ff',official_title:'#d9e9ff',date:'#ffe0cc',time:'#ffedd7',title:'#eee2f5',organization:'#deedf4',plant:'#e8f3cc',food:'#f8e4d8',artifact:'#ede6f7',keyword:'#f4efcc','key-word':'#f4efcc'};
  for(const type of READER_DATA.types)if(type.color)fills[type.markup_id]=type.color;
  const lines={person:'#d49a00',place:'#2f8c56',office:'#2b6fb8',date:'#c46227'};
  typeLabel = type => READER_TYPES.get(type)?.label || type;
  const annotations=new Map();
  READER_PAGE.paragraphs.forEach(p=>p.content.forEach(n=>{
    if(n.annotation)for(const ann of [n.annotation,...(n.annotation.keyword_annotations||[])])annotations.set(ann.id,{...ann,text:n.text,paragraph:p});
  }));
  document.querySelectorAll('.reader .entity').forEach(node=>{
    const tid=node.dataset.termId;
    if(tid)node.dataset.authorityId=tid;
    else{
      const aid='unlinked:'+node.dataset.id;
      const item={authority_id:aid,entity_text:node.dataset.name||node.textContent,canonical_name:node.dataset.normalized||node.textContent,entity_type:node.dataset.markupId||node.dataset.type,source:'Textoria',count:1};
      authorityById.set(aid,item);node.dataset.authorityId=aid;
    }
    const type=node.dataset.markupId||node.dataset.type;
    node.style.setProperty('--entity-fill',fills[type]||'#e9edf3');
    node.setAttribute('tabindex','0');node.setAttribute('role','button');node.setAttribute('aria-label',`${node.dataset.name||node.textContent}，查看實體資訊`);
    node.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();selectAuthority(node.dataset.authorityId,false,node);}});
  });
  const storageKey='textoria.reader.'+READER_DATA.collection_id;
  function readPrefs(){try{return JSON.parse(sessionStorage.getItem(storageKey)||'{}');}catch{return {};}}
  const prefs=readPrefs();
  const expanded=new Set();
  let selectedId=prefs.selectedId||null;
  function savePrefs(){try{sessionStorage.setItem(storageKey,JSON.stringify({expanded:[...expanded],selectedId,leftCollapsed:document.body.classList.contains('left-collapsed'),rightCollapsed:document.body.classList.contains('right-collapsed')}));}catch{}}
  const chapterCounts=new Map();
  for(const p of READER_PAGE.paragraphs)for(const n of p.content){
    if(!n.annotation)continue;
    for(const ann of [n.annotation,...(n.annotation.keyword_annotations||[])]){
      const ids=new Set([ann.term_id,...(ann.term_alternatives||[]).map(a=>a.term_id)].filter(Boolean));
      for(const id of ids)chapterCounts.set(id,(chapterCounts.get(id)||0)+1);
    }
  }
  function renderEntityTree(){
    const tree=document.getElementById('entityTree');tree.replaceChildren();
    const q=document.getElementById('entityFilter').value.trim();
    let groups=0;
    for(const spec of READER_DATA.types.filter(t=>t.kind==='element')){
      const items=AUTHORITY.map(t=>({...t,shownCount:t.count})).filter(t=>t.shownCount>0&&(t.markup_ids||[t.entity_type]).includes(spec.markup_id)&&(!q||t.canonical_name.includes(q)||(t.aliases||[]).some(a=>(a.text||a).includes(q)))).sort((a,b)=>b.shownCount-a.shownCount||a.canonical_name.localeCompare(b.canonical_name,'zh-Hant'));
      if(!items.length)continue;groups++;
      const group=document.createElement('details');group.className='entity-group';group.dataset.type=spec.markup_id;group.open=q?true:expanded.has(spec.markup_id);
      const summary=document.createElement('summary');
      const swatch=document.createElement('span');swatch.className='swatch';swatch.style.background=fills[spec.markup_id]||'#e9edf3';swatch.style.color=lines[spec.markup_id]||'#8b93a0';
      const label=document.createElement('span');label.textContent=spec.label;
      const count=document.createElement('span');count.className='entity-group-count';count.textContent=items.length;count.title='全書詞條數';
      summary.append(swatch,label,count);group.append(summary);
      const list=document.createElement('ul');list.className='entity-term-list';
      for(const item of items){
        const li=document.createElement('li'),button=document.createElement('button');button.type='button';button.className='entity-term';button.dataset.authorityId=item.authority_id;button.classList.toggle('is-current',item.authority_id===selectedId);
        const name=document.createElement('span');name.textContent=item.canonical_name;name.title=item.canonical_name;
        const n=document.createElement('span');n.className='freq-count';n.textContent=item.shownCount;n.title='全書出現次數';
        button.append(name,n);button.onclick=()=>selectAuthority(item.authority_id,true);li.append(button);list.append(li);
      }
      group.append(list);group.addEventListener('toggle',()=>{if(q||!group.isConnected)return;if(group.open)expanded.add(spec.markup_id);else expanded.delete(spec.markup_id);savePrefs();});tree.append(group);
    }
    if(!groups){const empty=document.createElement('div');empty.className='empty';empty.textContent=q?'沒有符合的詞條。':'尚無實體標註。';tree.append(empty);}
  }
  document.getElementById('entityFilter').addEventListener('input',renderEntityTree);
  initStats = () => {
    document.getElementById('totalEntities').textContent=READER_DATA.terms.length.toLocaleString();
    document.getElementById('totalMentions').textContent=READER_DATA.total_annotations.toLocaleString();
  };
  initFrequencyList = renderEntityTree;
  const occurrenceData=window.TEXTORIA_OCCURRENCES;
  async function copyText(context){
    if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(context);return;}
    const field=document.createElement('textarea');field.value=context;field.style.position='fixed';field.style.opacity='0';document.body.append(field);field.select();
    const ok=document.execCommand('copy');field.remove();if(!ok)throw new Error('copy');
  }
  function selectionLocation(selection){
    if(!selection||selection.isCollapsed||selection.rangeCount!==1)return {error:'先選取正文中的未標註文字'};
    const range=selection.getRangeAt(0);
    const parent=node=>node.nodeType===Node.ELEMENT_NODE?node:node.parentElement;
    const first=parent(range.startContainer)?.closest('.reader [data-paragraph-number][id]'),last=parent(range.endContainer)?.closest('.reader [data-paragraph-number][id]');
    if(!first||first!==last)return {error:'請選取同一段落內的文字'};
    const prefix=document.createRange();prefix.selectNodeContents(first);prefix.setEnd(range.startContainer,range.startOffset);
    function sourceOffset(container,offset){
      const mapped=parent(container)?.closest('[data-source-start]');
      if(!mapped)return null;
      const local=document.createRange();local.selectNodeContents(mapped);local.setEnd(container,offset);
      return Number(mapped.dataset.sourceStart)+Array.from(local.toString()).length;
    }
    const text=range.toString(),mappedStart=sourceOffset(range.startContainer,range.startOffset),mappedEnd=sourceOffset(range.endContainer,range.endOffset);
    const start=mappedStart??Array.from(prefix.toString()).length,end=mappedEnd??(start+Array.from(text).length);
    if(mappedStart!==null&&end-start!==Array.from(text).length)return {error:'請選取同一註解或表格儲存格內的連續文字'};
    if(!text.trim())return {error:'先選取正文中的未標註文字'};
    for(const entity of first.querySelectorAll('.entity')){
      const before=document.createRange();before.selectNodeContents(first);before.setEndBefore(entity);
      const mapped=entity.closest('[data-source-start]');
      const left=mapped?Number(mapped.dataset.sourceStart):Array.from(before.toString()).length,right=left+Array.from(entity.textContent).length;
      if(start<right&&end>left)return {error:'選取範圍已有標註，請點該實體使用複製圖示修改'};
    }
    return {paragraphId:first.id,number:first.dataset.paragraphNumber,divisionId:first.closest('article[id]').id,start,end,text};
  }
  const addButton=document.getElementById('addEntity');let selectedTextLocation=null,selectionToastTimer;
  function updateTextSelection(){
    const result=selectionLocation(window.getSelection());selectedTextLocation=result.error?null:result;
    addButton.disabled=!selectedTextLocation;addButton.title=result.error||'新增實體：複製選取文字與位置';
  }
  if(addButton){
  document.addEventListener('selectionchange',updateTextSelection);
  addButton.addEventListener('pointerdown',event=>event.preventDefault());
  addButton.onclick=async()=>{
    if(!selectedTextLocation)return;
    const selection=selectedTextLocation;
    const title=chapterLabel(selection.divisionId);
    const payload=`你要將下列選取文字新增為哪種類型的實體？請說明：\n${title} 第${selection.number}段「${selection.text}」\n選取定位｜段落 ID：${selection.paragraphId}｜範圍：[${selection.start},${selection.end})（Unicode 字元，從 0 起算）｜原文：${selection.text}`;
    const status=document.getElementById('selectionCopyStatus');clearTimeout(selectionToastTimer);
    try{await copyText(payload);status.textContent='已複製選取資訊，請貼到 Codex 並說明實體類型。';}
    catch{status.textContent='複製失敗，請重新選取後再試。';}
    status.hidden=false;selectionToastTimer=setTimeout(()=>status.hidden=true,3500);
  };
  }
  for(const [buttonId,extension,label] of [['exportHtml','html','單檔 HTML'],['exportTable','table','CSV／Excel 詮釋資料表'],['exportDocuxml','docuxml','DocuXML']]){
    document.getElementById(buttonId)?.addEventListener('click',async()=>{
      const title=READER_DATA.collection_title||document.querySelector('header h1').textContent;
      const details=extension==='html'?'請保留左右欄、章節選單與實體定位，CSS、JS 內嵌；移除頂端標註與匯出圖示。':extension==='table'?'請同時提供 CSV、Excel，採 DocuSky metadata 欄位，第一層章節一列，filename 與 DocuXML 一致。':'請以第一層章節為一件，包含全部下層章節、段落及已套用標註。';
      const outputNames=extension==='html'?`${title}.html`:extension==='table'?`${title}_metadata.csv、${title}_metadata.xlsx`:`${title}_docu.xml`;
      const payload=`請將文獻集「${title}」的最新資料匯出為${label}，檔名「${outputNames}」。\n${details}\n請保留章節、段落、實體與標註 ID，完成後提供檔案連結。\n文獻集 ID：${READER_DATA.collection_id}`;
      const status=document.getElementById('selectionCopyStatus');clearTimeout(selectionToastTimer);
      try{await copyText(payload);status.textContent=`已複製${label}匯出指令，請貼到 Codex 對話框。`;}
      catch{status.textContent='複製失敗，請到操作說明複製匯出範例。';}
      status.hidden=false;selectionToastTimer=setTimeout(()=>status.hidden=true,4000);
    });
  }
  document.getElementById('publishSite')?.addEventListener('click',async()=>{
    const title=READER_DATA.collection_title||document.querySelector('header h1').textContent;
    const payload=`請使用 ChatGPT／Sites，將文獻集「${title}」的最新標註成果建立並發布為網站。\n先從目前 corpus.json 產生展示版 HTML，保留原有版面、左右欄、章節選單、實體資訊、KWIC 定位及右上角全部圖示與操作說明頁。圖示只複製指令，不直接編輯網站或標註資料；實體樹初次開啟與切換章節後全部收合。\n請以此閱讀版作為網站首頁，使用 Sites 支援的部署流程，預設建立私人網站，不修改本機正文與標註，也不上傳 uploads、clean、corpus.json 或歷史備份。網站仍包含全文與標註資料。\n完成後提供已驗證的網站網址；若目前環境沒有 Sites 功能，請明確說明，並提供單檔 HTML，不要改用其他平台發布。\n文獻集 ID：${READER_DATA.collection_id}`;
    const status=document.getElementById('selectionCopyStatus');clearTimeout(selectionToastTimer);
    try{await copyText(payload);status.textContent='已複製建立 ChatGPT 網站指令，請貼到 Codex 對話框。';}
    catch{status.textContent='複製失敗，請到操作說明複製建立網站範例。';}
    status.hidden=false;selectionToastTimer=setTimeout(()=>status.hidden=true,4000);
  });
  const copyIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></svg>';
  function copyButton(id,context,iconOnly=false){
    const button=document.createElement('button');button.type='button';button.className='copy-id';button.textContent=id;button.title='複製編號與定位資訊';button.setAttribute('aria-label','複製 '+id);
    if(iconOnly){button.className='copy-location';button.innerHTML=copyIcon;button.title='複製定位資訊';}
    let resetTimer;
    const restore=()=>{if(iconOnly)button.innerHTML=copyIcon;else button.textContent=id;button.title=iconOnly?'複製定位資訊':'複製編號與定位資訊';};
    button.onclick=async()=>{
      clearTimeout(resetTimer);
      try{
        await copyText(context);
        if(iconOnly){button.innerHTML='<span aria-hidden="true">✓</span>';button.title='已複製';}else button.textContent='已複製';resetTimer=setTimeout(restore,1200);
      }catch{if(iconOnly){button.textContent='!';button.title='複製失敗';}else button.textContent='複製失敗';resetTimer=setTimeout(restore,1600);}
    };return button;
  }
  function chapterLabel(id){const title=occurrenceData.chapters[id]||id;return title.match(/^第[一二三四五六七八九十百零〇0-9]+回/)?.[0]||title;}
  function paragraphRows(all,current){
    const seen=new Set(current?[current[1]]:[]);
    return [...(current?[current]:[]),...all.filter(row=>{if(seen.has(row[1]))return false;seen.add(row[1]);return true;})];
  }
  function occurrenceContext(item,row,isCurrent){
    const [aid,pid,did,number,,hit]=row;
    const heading=`${chapterLabel(did)} 第${number}段 ${item.canonical_name}（原文：${hit}）`;
    return (isCurrent?'你要針對下列實體做什麼處理？請說明：':'你要針對下列段落的實體做什麼處理？請說明:')+'\n'+heading+'\n'+(isCurrent?'目前選取的實體標註':'此段中的實體標註')+`｜實體 ID：${item.authority_id}｜段落 ID：${pid}`+(isCurrent?`｜標註 ID：${aid}`:'');
  }
  function locateMention(node){
    node.focus({preventScroll:true});
    node.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});
  }
  function goToOccurrence(item,row){
    const [aid,pid,did]=row;
    const node=document.querySelector('.reader .entity[data-id="'+CSS.escape(aid)+'"]');
    if(node){if(singleFile)showStandaloneChapter(did,false);selectAuthority(item.authority_id,false,node);locateMention(node);return;}
    if(did!==document.querySelector('.reader article[id]').id){
      savePrefs();const link=[...document.querySelectorAll('#chapterLinks .toc-link')].find(a=>new URL(a.href).pathname.endsWith('/'+did+'.html'));
      if(link){const url=new URL(link.href);url.hash='';url.searchParams.set('mention',aid);url.searchParams.set('term',item.authority_id);location.assign(url.href);}return;
    }
  }
  renderDetail = (item,count,sourceNode=null) => {
    const ann=sourceNode?annotations.get(sourceNode.dataset.id):null;
    const all=occurrenceData.terms[item.authority_id]||[];
    const rows=[['類型',(ann?.markup_ids||item.markup_ids||[item.entity_type]).map(typeLabel).join('／')],['別名',(item.aliases||[]).map(a=>typeof a==='string'?a:a.text).filter(a=>a!==item.canonical_name).join('、')],['衝突說明',ann?.conflict_note||all.find(r=>r[7])?.[7]]].filter(([,v])=>v);
    const detail=document.getElementById('detail');detail.className='';detail.replaceChildren();
    const heading=document.createElement('div');heading.className='entity-heading';
    const name=document.createElement('h4');name.className='detail-title';name.textContent=item.canonical_name||item.entity_text;heading.append(name,copyButton(item.canonical_name,`你要對文本中的下列實體做什麼處理？請說明:\n實體 ${item.authority_id}｜${item.canonical_name}｜${(item.markup_ids||[item.entity_type]).map(typeLabel).join('／')}`,true));detail.append(heading);
    const summary=document.createElement('p');summary.className='entity-occurrence-summary';summary.textContent=`出現 ${all.length.toLocaleString()} 次｜段落 ${new Set(all.map(row=>row[1])).size.toLocaleString()} 段`;detail.append(summary);
    const table=document.createElement('table');table.className='detail-table';table.innerHTML=rows.map(([k,v])=>`<tr><th>${esc(k)}</th><td class="detail-text">${esc(v)}</td></tr>`).join('');detail.append(table);
    const list=document.getElementById('occurrenceList');list.replaceChildren();
    const currentId=sourceNode?.dataset.id;
    const current=all.find(r=>r[0]===currentId);
    const ordered=paragraphRows(all,current);
    document.getElementById('occurrenceSection').hidden=false;
    let rendered=0;
    function appendBatch(){
      list.querySelector('.kwic-more-row')?.remove();
      for(const row of ordered.slice(rendered,rendered+80)){
        const [aid,pid,did,number,before,hit,after]=row;
        const li=document.createElement('li');li.className='kwic-item';li.classList.toggle('is-current',aid===currentId);
        const line=document.createElement('div');line.className='kwic-heading';
        const link=document.createElement('button');link.type='button';link.className='kwic-location';link.textContent=`${chapterLabel(did)} 第${number}段`;link.title=occurrenceData.chapters[did];link.onclick=()=>goToOccurrence(item,row);line.append(link);
        line.append(copyButton(`${chapterLabel(did)} 第${number}段 ${item.canonical_name}`,occurrenceContext(item,row,aid===currentId),true));
        if(aid===currentId){const badge=document.createElement('span');badge.className='kwic-current';badge.textContent='目前選取';line.append(badge);}li.append(line);
        const snippet=document.createElement('button');snippet.type='button';snippet.className='kwic-snippet';snippet.title=before+hit+after;snippet.append(document.createTextNode(before));
        const mark=document.createElement('mark');mark.textContent=hit;mark.style.background=fills[item.entity_type]||'#e9edf3';snippet.append(mark,document.createTextNode(after));snippet.onclick=()=>goToOccurrence(item,row);li.append(snippet);list.append(li);
      }
      rendered=Math.min(rendered+80,ordered.length);
      if(rendered<ordered.length){const li=document.createElement('li');li.className='kwic-more-row';const b=document.createElement('button');b.type='button';b.className='kwic-more';b.textContent=`顯示更多（尚有 ${ordered.length-rendered} 段）`;b.onclick=appendBatch;li.append(b);list.append(li);}
    }
    appendBatch();
    if(!ordered.length){const li=document.createElement('li');li.className='empty';li.textContent='尚無此實體的標註。';list.append(li);}
    document.getElementById('mapSection').hidden=true;
  };
  selectAuthority = (id,scroll=false,node=null) => {
    const item=authorityById.get(id);if(!item)return;selectedId=id;expandRightPanel();savePrefs();
    document.querySelectorAll('.entity-term').forEach(b=>b.classList.toggle('is-current',b.dataset.authorityId===id));
    document.querySelectorAll('.entity.is-selected').forEach(n=>n.classList.remove('is-selected'));
    const matches=[...document.querySelectorAll(`.reader .entity[data-authority-id="${CSS.escape(id)}"]`)].filter(n=>!singleFile||!n.closest('article[id]').hidden);const active=node||matches[0]||null;if(active)active.classList.add('is-selected');
    renderDetail(item,matches.length,active);
    if(scroll&&active)locateMention(active);
  };
  const chapterLinks=[...document.querySelectorAll('#chapterLinks .toc-link')];
  const select=document.getElementById('chapterSelect');
  const currentId=singleFile?.currentId||document.querySelector('.reader article[id]').id;
  let currentIndex=-1;
  const picker=document.querySelector('.chapter-picker');
  const pickerButton=document.getElementById('chapterPickerButton');
  const pickerList=document.getElementById('chapterOptions');
  const pickerChoices=[];
  let focusedChapter=-1,typeAhead='',typeAheadTimer;
  function chapterStyle(node,level){
    node.style.fontSize=`${[18,16,14,12][Math.min(level-1,3)]}px`;
    node.style.paddingLeft=`${12+16*Math.min(level-1,2)}px`;
  }
  chapterLinks.forEach((link,i)=>{
    const id=link.dataset.divisionId||new URL(link.href).pathname.split('/').pop().replace('.html','');
    const level=Math.max(1,Number(link.dataset.level)||1);
    const title=link.textContent.trim();
    const option=document.createElement('option');option.value=link.href;option.textContent=title;
    const choice=document.createElement('button');choice.type='button';choice.className='chapter-choice';
    choice.setAttribute('role','option');choice.setAttribute('aria-selected',String(id===currentId));
    choice.setAttribute('aria-label',`第 ${level} 層：${title}`);choice.tabIndex=-1;
    choice.textContent=title;choice.dataset.level=level;chapterStyle(choice,level);
    choice.addEventListener('click',()=>{closeChapterPicker();navigateChapter(i);});
    pickerList.append(choice);pickerChoices.push(choice);
    if(id===currentId){option.selected=true;currentIndex=i;pickerButton.textContent=title;chapterStyle(pickerButton,level);}
    select.append(option);
  });
  function showStandaloneChapter(id,scroll=true){
    if(!singleFile?.chapters[id])return;
    if(singleFile.currentId!==id){expanded.clear();document.getElementById('entityFilter').value='';renderEntityTree();savePrefs();}
    singleFile.currentId=id;const shown=new Set(singleFile.chapters[id]);
    document.querySelectorAll('.reader article[id]').forEach(a=>a.hidden=!shown.has(a.id));
    currentIndex=chapterLinks.findIndex(link=>link.dataset.divisionId===id);
    select.selectedIndex=currentIndex;
    pickerChoices.forEach((choice,index)=>choice.setAttribute('aria-selected',String(index===currentIndex)));
    const choice=pickerChoices[currentIndex];if(choice){pickerButton.textContent=choice.textContent;chapterStyle(pickerButton,Number(choice.dataset.level));}
    document.getElementById('previousChapter').disabled=currentIndex<=0;
    document.getElementById('nextChapter').disabled=currentIndex>=chapterLinks.length-1;
    try{history.replaceState(null,'','#'+id);}catch{}
    if(scroll)window.scrollTo({top:0,behavior:'instant'});
    if(selectedId&&authorityById.has(selectedId))selectAuthority(selectedId,false);
  }
  function navigateChapter(index){if(index<0||index>=chapterLinks.length)return;expanded.clear();document.getElementById('entityFilter').value='';savePrefs();if(singleFile){showStandaloneChapter(chapterLinks[index].dataset.divisionId);return;}history.scrollRestoration='manual';location.assign(chapterLinks[index].href);}
  select.onchange=()=>navigateChapter(select.selectedIndex);
  function focusChapter(index){
    if(!pickerChoices.length)return;
    focusedChapter=Math.max(0,Math.min(index,pickerChoices.length-1));
    pickerChoices[focusedChapter].focus({preventScroll:true});
    pickerChoices[focusedChapter].scrollIntoView({block:'nearest',inline:'nearest'});
  }
  function openChapterPicker(index=currentIndex){
    pickerList.hidden=false;pickerButton.setAttribute('aria-expanded','true');
    focusChapter(index<0?0:index);
  }
  function closeChapterPicker(restoreFocus=false){
    pickerList.hidden=true;pickerButton.setAttribute('aria-expanded','false');
    typeAhead='';clearTimeout(typeAheadTimer);
    if(restoreFocus)pickerButton.focus({preventScroll:true});
  }
  pickerButton.addEventListener('click',()=>pickerList.hidden?openChapterPicker():closeChapterPicker(true));
  pickerButton.addEventListener('keydown',event=>{
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      event.preventDefault();openChapterPicker();
    }
  });
  pickerList.addEventListener('keydown',event=>{
    if(event.key==='Escape'){event.preventDefault();event.stopPropagation();closeChapterPicker(true);return;}
    if(event.key==='Tab'){closeChapterPicker();pickerButton.focus({preventScroll:true});return;}
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      event.preventDefault();focusChapter(focusedChapter+(event.key==='ArrowDown'?1:-1));return;
    }
    if(event.key==='Home'||event.key==='End'){
      event.preventDefault();focusChapter(event.key==='Home'?0:pickerChoices.length-1);return;
    }
    if(event.key.length===1&&event.key!==' '&&!event.ctrlKey&&!event.metaKey&&!event.altKey){
      event.preventDefault();typeAhead+=event.key.toLocaleLowerCase();clearTimeout(typeAheadTimer);
      typeAheadTimer=setTimeout(()=>{typeAhead='';},700);
      const start=focusedChapter+1;
      for(let step=0;step<pickerChoices.length;step++){
        const index=(start+step)%pickerChoices.length;
        if(pickerChoices[index].textContent.toLocaleLowerCase().startsWith(typeAhead)){focusChapter(index);break;}
      }
    }
  });
  picker.addEventListener('focusout',event=>{if(!picker.contains(event.relatedTarget))closeChapterPicker();});
  document.addEventListener('pointerdown',event=>{if(!picker.contains(event.target))closeChapterPicker();});
  document.getElementById('previousChapter').disabled=currentIndex<=0;
  document.getElementById('nextChapter').disabled=currentIndex>=chapterLinks.length-1;
  document.getElementById('previousChapter').onclick=()=>navigateChapter(currentIndex-1);
  document.getElementById('nextChapter').onclick=()=>navigateChapter(currentIndex+1);
  if(singleFile)window.addEventListener('hashchange',()=>showStandaloneChapter(location.hash.slice(1)));
  // Start with all categories collapsed; help return restores its saved state.
  initStats();initFrequencyList();initEntityClicks();initPanelToggles();
  if(typeof prefs.leftCollapsed==='boolean')document.body.classList.toggle('left-collapsed',prefs.leftCollapsed);
  if(typeof prefs.rightCollapsed==='boolean')document.body.classList.toggle('right-collapsed',prefs.rightCollapsed);
  updatePanelToggleIcons();
  savePrefs();
  for(const id of ['toggleLeft','toggleRight'])document.getElementById(id).addEventListener('click',savePrefs);
  const targetParams=new URLSearchParams(location.search);
  const targetNode=targetParams.get('mention')?document.querySelector('.reader .entity[data-id="'+CSS.escape(targetParams.get('mention'))+'"]'):null;
  if(targetNode){selectAuthority(targetParams.get('term')||targetNode.dataset.authorityId,false,targetNode);const restoreTarget=()=>requestAnimationFrame(()=>locateMention(targetNode));if(document.readyState==='complete')restoreTarget();else window.addEventListener('load',restoreTarget,{once:true});}
  else if(selectedId&&authorityById.has(selectedId)&&!document.body.classList.contains('right-collapsed'))selectAuthority(selectedId,false);
  const helpReturnKey='textoria.reader.helpReturn';
  document.getElementById('readerHelp')?.addEventListener('click',()=>{
    savePrefs();
    try{sessionStorage.setItem(helpReturnKey,JSON.stringify({
      collectionId:READER_DATA.collection_id,url:location.href,x:window.scrollX,y:window.scrollY,
      selectedId,mentionId:document.querySelector('.reader .entity.is-selected')?.dataset.id||null,
      filter:document.getElementById('entityFilter').value,
      expanded:[...expanded],leftCollapsed:document.body.classList.contains('left-collapsed'),rightCollapsed:document.body.classList.contains('right-collapsed'),
      leftScroll:document.querySelector('.chapter-panel').scrollTop,rightScroll:document.querySelector('.inspector').scrollTop,
      shownParagraphs:document.querySelectorAll('#occurrenceList .kwic-item').length
    }));}catch{}
  });
  window.addEventListener('pageshow',async event=>{
    let state;try{state=JSON.parse(sessionStorage.getItem(helpReturnKey)||'null');}catch{return;}
    if(!state||state.collectionId!==READER_DATA.collection_id||state.url!==location.href)return;
    if(!event.persisted){
      expanded.clear();for(const type of state.expanded||[])expanded.add(type);
      document.getElementById('entityFilter').value=state.filter||'';
      selectedId=state.selectedId;renderEntityTree();
      const mention=state.mentionId?document.querySelector('.reader .entity[data-id="'+CSS.escape(state.mentionId)+'"]'):null;
      if(selectedId&&authorityById.has(selectedId))selectAuthority(selectedId,false,mention);
      while(document.querySelectorAll('#occurrenceList .kwic-item').length<(state.shownParagraphs||0)){
        const more=document.querySelector('#occurrenceList .kwic-more');if(!more)break;more.click();
      }
      document.body.classList.toggle('left-collapsed',!!state.leftCollapsed);
      document.body.classList.toggle('right-collapsed',!!state.rightCollapsed);
      updatePanelToggleIcons();savePrefs();
    }
    if(document.fonts)await document.fonts.ready;
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      window.scrollTo({left:state.x||0,top:state.y||0,behavior:'instant'});
      document.querySelector('.chapter-panel').scrollTop=state.leftScroll||0;
      document.querySelector('.inspector').scrollTop=state.rightScroll||0;
      try{sessionStorage.removeItem(helpReturnKey);}catch{}
    }));
  });
  const header=document.querySelector('header');
  new ResizeObserver(()=>{
    const h=header.getBoundingClientRect().height;document.documentElement.style.setProperty('--reader-header-height',h+'px');
    const footerHeight=document.querySelector('footer').getBoundingClientRect().height;
    for(const panel of document.querySelectorAll('.chapter-panel,.inspector')){panel.style.top=h+'px';panel.style.height=`calc(100vh - ${h}px - ${footerHeight}px)`;}
  }).observe(header);
})();
