import React, { useEffect, useRef, useState } from 'react';
import { ArrowRight, ArrowUpRight, BookOpen, Check, CheckCircle, Copy, Database, DownloadSimple, Export, FileText, GithubLogo, Info, List, ListBullets, MagnifyingGlass, PencilSimple, Plus, SlidersHorizontal, User, X } from '@phosphor-icons/react';
import { product } from './product';
import guideSections from './guide.json';

const icons = { file: FileText, list: ListBullets, check: CheckCircle, user: User, pencil: PencilSimple, search: MagnifyingGlass, database: Database, sliders: SlidersHorizontal, export: Export };
const demoText = '建安十三年，曹操率大軍南下，欲定江東。劉備與孫權結盟，於赤壁與曹軍相持。時有將領，名曰周瑜，乃定火攻之計；東南風起，戰局遂變。此戰之後，天下形勢為之一變。';
const demoPeople = ['曹操', '劉備', '孫權', '周瑜'];

function CopyButton({ text, label = '複製指令', className = '' }) {
  const [copied, setCopied] = useState(false), [error, setError] = useState(false);
  const timer = useRef();
  useEffect(() => () => clearTimeout(timer.current), []);
  async function copy() {
    try { await navigator.clipboard.writeText(text); setCopied(true); setError(false); clearTimeout(timer.current); timer.current = setTimeout(() => setCopied(false), 2200); }
    catch { setError(true); }
  }
  return <span className="copy-wrap"><button className={`copy-button ${className}`} onClick={copy}>{copied ? <Check size={17} /> : <Copy size={17} />} {copied ? '已複製' : label}</button><span role="status" className={error ? 'copy-error' : 'sr-only'}>{error ? '無法存取剪貼簿，請選取文字手動複製。' : copied ? '已複製到剪貼簿' : ''}</span></span>;
}
function InstallDialog({ dialogRef }) {
  return <dialog ref={dialogRef} className="install-dialog" aria-labelledby="install-heading" onClick={e => { if (e.target === dialogRef.current) dialogRef.current.close(); }}><div className="dialog-inner"><button className="icon-button close-dialog" aria-label="關閉安裝說明" onClick={() => dialogRef.current.close()}><X size={22} /></button><div className="icon-tile"><DownloadSimple size={28} /></div><p className="eyebrow">GET STARTED</p><h2 id="install-heading">{product.install.title}</h2><p>{product.install.description}</p><div className="install-notice"><Info size={20} /><span>{product.install.notice}</span></div><p className="code-label">貼到 Codex 的專案對話</p><pre className="install-code">{product.install.command}</pre><CopyButton text={product.install.command} label="複製安裝指令" className="button primary" /><p className="requirements">{product.install.requirements}</p></div></dialog>;
}
function Demo() {
  const [tab, setTab] = useState(0), [selected, setSelected] = useState('曹操');
  const active = product.examples[tab], matches = active.hits;
  function changeTab(index) { setTab(index); setSelected(product.examples[index].hits[0]); }
  function onTabKey(e, index) {
    let next = index;
    if (e.key === 'ArrowRight') next = (index + 1) % product.examples.length;
    else if (e.key === 'ArrowLeft') next = (index + product.examples.length - 1) % product.examples.length;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = product.examples.length - 1;
    else return;
    e.preventDefault(); changeTab(next); document.getElementById(`example-tab-${next}`).focus();
  }
  const pattern = new RegExp(`(${matches.map(s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'g');
  const fragments = demoText.split(pattern), contexts = [];
  let start = demoText.indexOf(selected);
  while (start >= 0) { contexts.push({ before: demoText.slice(Math.max(0, start - 8), start), after: demoText.slice(start + selected.length, start + selected.length + 10) }); start = demoText.indexOf(selected, start + 1); }
  return <section className="section examples" id="examples" aria-labelledby="examples-heading"><div className="section-heading"><p className="eyebrow">SEE IT IN ACTION</p><h2 id="examples-heading">從你的詞表，到可核對的結果。</h2><p>選一種輸入方式，再點選標註文字，看看它的上下文。</p></div><div className="example-tabs" role="tablist" aria-label="範例輸入方式">{product.examples.map((item, index) => <button key={item.id} id={`example-tab-${index}`} role="tab" aria-selected={tab === index} aria-controls="example-panel" tabIndex={tab === index ? 0 : -1} onKeyDown={e => onTabKey(e, index)} onClick={() => changeTab(index)}>{item.title}</button>)}</div><div className="example-workspace" id="example-panel" role="tabpanel" aria-labelledby={`example-tab-${tab}`}><div className="example-input"><div className="panel-title"><FileText size={20} /><span>{active.label}</span></div><pre>{active.source}</pre><div className="prompt"><span className="code-label">對話指令</span><p>{active.prompt}</p><CopyButton text={active.prompt} /></div></div><div className="example-result"><div className="panel-title"><BookOpen size={20} /><span>標註結果</span><span className="demo-badge">互動示範</span></div><h3>赤壁之戰</h3><p className="demo-paragraph">{fragments.map((part, index) => matches.includes(part) ? <button key={index} aria-label={`查看「${part}」的上下文`} aria-pressed={selected === part} className={`term ${tab === 1 ? 'keyword' : demoPeople.includes(part) ? 'person' : 'place'} ${selected === part ? 'is-selected' : ''}`} onClick={() => setSelected(part)}>{part}</button> : part)}</p><div className="kwic"><div className="kwic-heading"><span>關鍵詞上下文 <small>KWIC</small></span><strong>{selected}</strong></div>{contexts.map((context, i) => <p key={i}><span>… {context.before}</span><mark>{selected}</mark><span>{context.after} …</span></p>)}</div><p className="demo-note">節錄式示範文本，展示字面比對與定位方式；不會寫入專案資料。</p></div></div></section>;
}
export function App() {
  const [menuOpen, setMenuOpen] = useState(false), [guide, setGuide] = useState('start');
  const dialogRef = useRef(null), guideHeading = useRef(null);
  const currentGuide = guideSections.find(s => s.id === guide) || guideSections[0];
  function showGuide(id = 'start') { setGuide(id); setMenuOpen(false); requestAnimationFrame(() => { document.getElementById('guide-details').scrollIntoView({ behavior: 'smooth', block: 'start' }); guideHeading.current?.focus({ preventScroll: true }); }); }
  function install() { setMenuOpen(false); if (product.actionUrl) window.location.assign(product.actionUrl); else dialogRef.current.showModal(); }
  return <><a className="skip-link" href="#main">跳到主要內容</a><header className="site-header"><a className="brand" href="#top" aria-label={`${product.name} 首頁`}><FileText size={35} weight="fill" className="brand-icon" /><span>{product.name}</span></a><nav className={`main-nav ${menuOpen ? 'is-open' : ''}`} aria-label="主要導覽" id="main-nav"><a href="#features" onClick={() => setMenuOpen(false)}>功能</a><a href="#workflow" onClick={() => setMenuOpen(false)}>使用流程</a><button onClick={() => showGuide()}>使用指南</button><a href="#examples" onClick={() => setMenuOpen(false)}>範例</a></nav><button className="button primary header-cta" onClick={install}>{product.primaryAction}</button><button className="icon-button mobile-menu" aria-label={menuOpen ? '關閉選單' : '開啟選單'} aria-expanded={menuOpen} aria-controls="main-nav" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={24} /> : <List size={24} />}</button></header>
    <main id="main"><section className="hero" id="top"><div className="hero-copy"><p className="eyebrow">{product.eyebrow}</p><h1>{product.headline.map((line, i) => <React.Fragment key={line}>{i > 0 && <br />}{line}</React.Fragment>)}</h1><p className="hero-description">{product.description}</p><div className="hero-actions"><button className="button primary" onClick={install}>{product.primaryAction}<ArrowRight size={20} /></button><a className="button secondary" href="#examples">{product.secondaryAction}</a></div></div><figure className="product-preview"><img src={product.image} alt={product.imageAlt} width="1440" height="900" fetchPriority="high" /><figcaption>{product.imageCaption}</figcaption></figure></section>
    <section className="workflow page-width" id="workflow" aria-label="使用流程">{product.steps.map((step, index) => { const Icon = icons[step.icon]; return <article className="workflow-step" key={step.title}><div className="step-icons"><span className="step-number">{index + 1}</span><Icon size={38} /></div><h2>{step.title}</h2><p>{step.description}</p></article>; })}</section>
    <section className="guide-gateway" id="features"><div className="page-width"><div className="section-heading"><h2>操作說明，從這裡開始。</h2><p>依主題閱讀使用指南，快速上手 {product.name}。</p></div><div className="topic-grid">{product.topics.map(topic => { const Icon = icons[topic.icon]; return <button className="topic" key={topic.id} onClick={() => showGuide(topic.id)}><span className="icon-tile"><Icon size={29} /></span><strong>{topic.title}</strong><span>{topic.description}</span></button>; })}</div><button className="button primary" onClick={() => showGuide()}>閱讀完整指南<ArrowRight size={19} /></button></div></section>
    <Demo />
    <section className="section full-guide" id="guide-details" aria-labelledby="guide-heading"><div className="guide-top"><div><p className="eyebrow">THE FIELD GUIDE</p><h2 id="guide-heading" tabIndex={-1} ref={guideHeading}>每一步，都有說明。</h2><p>從第一個標註到成果分享，找到你現在需要的操作。</p></div><span className="guide-meta"><BookOpen size={18} />完整操作指南</span></div><div className="guide-layout"><nav className="guide-nav" aria-label="操作指南章節">{guideSections.map(section => <button key={section.id} aria-current={guide === section.id ? 'true' : undefined} onClick={() => setGuide(section.id)}>{section.title}<ArrowUpRight size={15} /></button>)}</nav><article className="guide-article" key={currentGuide.id} aria-label={currentGuide.title} dangerouslySetInnerHTML={{ __html: currentGuide.html }} /></div></section>
    <section className="section faq" id="faq"><div className="section-heading"><p className="eyebrow">GOOD TO KNOW</p><h2>開始之前，你可能想知道。</h2></div><div className="faq-list">{product.faq.map(item => <details key={item.question}><summary>{item.question}<Plus size={20} /></summary><p>{item.answer}</p></details>)}</div></section>
    <section className="closing-cta"><p className="eyebrow">YOUR NEXT CHAPTER</p><h2>讓下一份文本，<br />成為可延續的研究。</h2><p>從一份詞表開始，在原文裡核對每一個發現。</p><button className="button primary" onClick={install}>{product.primaryAction}<ArrowRight size={20} /></button><button className="text-link" onClick={() => showGuide()}>先閱讀使用指南<ArrowUpRight size={16} /></button></section></main>
    <footer className="site-footer page-width"><a className="brand" href="#top"><FileText size={27} weight="fill" className="brand-icon" /><span>{product.name}</span></a><p>閱讀、選取，再用對話標註。</p><div><a href={product.repository} target="_blank" rel="noopener noreferrer"><GithubLogo size={19} />GitHub<ArrowUpRight size={14} /></a><a href="#faq">FAQ</a><span>{product.license}</span></div></footer><InstallDialog dialogRef={dialogRef} /></>;
}
