/* Return to the exact reader URL saved before opening this guide. */
(() => {
  try{
    const state=JSON.parse(sessionStorage.getItem('textoria.reader.helpReturn')||'null');
    if(!state?.url)return;
    const url=new URL(state.url);
    if(url.origin!==location.origin||url.protocol!==location.protocol)return;
    for(const link of document.querySelectorAll('[data-reader-return]')){
      link.href=url.href;
      link.onclick=event=>{
        if(event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
        event.preventDefault();location.replace(url.href);
      };
    }
  }catch{/* Direct visits keep the ordinary reading-entry link. */}
})();
