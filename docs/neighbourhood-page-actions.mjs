export function initializePageActions(documentRef=globalThis.document,navigatorRef=globalThis.navigator,windowRef=globalThis.window){
  const shareButton=documentRef?.getElementById('share-page');
  const printButton=documentRef?.getElementById('print-page');
  const status=documentRef?.getElementById('page-action-status');
  if(!shareButton||!printButton||!status)return;

  const canonicalUrl=documentRef.querySelector('link[rel="canonical"]')?.href||windowRef?.location?.href||'';
  const announce=message=>{status.textContent=message;};
  const copyLink=async()=>{
    if(typeof navigatorRef?.clipboard?.writeText!=='function')return false;
    try{
      await navigatorRef.clipboard.writeText(canonicalUrl);
      announce('Neighbourhood link copied.');
      return true;
    }catch{return false;}
  };

  shareButton.addEventListener('click',async()=>{
    if(typeof navigatorRef?.share==='function'){
      try{
        await navigatorRef.share({title:documentRef.title,url:canonicalUrl});
        announce('Sharing options opened.');
        return;
      }catch(error){
        if(error?.name==='AbortError')return;
      }
    }
    if(await copyLink())return;
    announce("Sharing didn't open here. You can copy this page's address from your browser instead.");
  });
  printButton.addEventListener('click',()=>windowRef?.print?.());
}
