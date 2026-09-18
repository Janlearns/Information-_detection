chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    for (const [kind, context, label] of [['text', 'selection', 'teks'], ['image', 'image', 'foto'], ['video', 'video', 'video']]) {
      chrome.contextMenus.create({id: kind, title: `Scan ${label} dengan CekFakta`, contexts: [context]});
    }
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab?.id || !['text', 'image', 'video'].includes(info.menuItemId)) return;
  const id = crypto.randomUUID();
  const target = {tabId: tab.id, frameIds: [0]};
  try {
    await chrome.scripting.executeScript({target, files: ['popup.js']});
    await chrome.tabs.sendMessage(tab.id, {type: 'scan-start', id}, {frameId: 0});
    let payload = {kind: info.menuItemId, text: (info.selectionText || '').slice(0, 30000)};
    if (payload.kind === 'text') {
      const results = await chrome.scripting.executeScript({
        target: {tabId: tab.id, frameIds: [info.frameId || 0]},
        func: collectLinkedTerms
      });
      payload.linked_terms = results[0]?.result || [];
    }
    if (payload.kind !== 'text') {
      const results = await chrome.scripting.executeScript({
        target: {tabId: tab.id, frameIds: [info.frameId || 0]},
        func: collectMedia, args: [payload.kind, info.srcUrl || '']
      });
      payload = {...payload, ...results[0].result};
    }
    const response = await fetch('http://127.0.0.1:8000/api/scan/jobs', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload), signal: AbortSignal.timeout(240000)
    });
    const job = await response.json();
    if (!response.ok) throw new Error(typeof job.detail === 'string' ? job.detail : 'Permintaan scan tidak valid.');
    let result;
    const deadline = Date.now() + 1800000;
    while (Date.now() < deadline) {
      const poll = await fetch(`http://127.0.0.1:8000/api/scan/jobs/${encodeURIComponent(job.id)}`, {signal: AbortSignal.timeout(10000)});
      const state = await poll.json();
      if (!poll.ok) throw new Error(state.detail || 'Gagal membaca hasil scan.');
      if (state.status === 'done') { result = state.result; break; }
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
    if (!result) throw new Error('Scan melewati batas waktu. Model OCR mungkin masih diunduh; coba lagi setelah server selesai.');
    await chrome.tabs.sendMessage(tab.id, {type: 'scan-result', id, result}, {frameId: 0});
  } catch (error) {
    const message = error.name === 'TimeoutError' ? 'Scan melewati batas waktu. Coba lagi.' :
      error instanceof TypeError ? 'Server lokal belum tersambung. Jalankan start-desktop.cmd lalu coba lagi.' : error.message;
    try { await chrome.tabs.sendMessage(tab.id, {type: 'scan-error', id, message}, {frameId: 0}); }
    catch { await chrome.action.setBadgeText({tabId: tab.id, text: '!'}); }
  }
});

function collectLinkedTerms() {
  const selection = window.getSelection();
  if (!selection?.rangeCount) return [];
  const terms = new Set();
  for (let i = 0; i < selection.rangeCount; i++) {
    const range = selection.getRangeAt(i);
    const ancestor = range.commonAncestorContainer;
    const container = ancestor.nodeType === 1 ? ancestor : ancestor.parentElement;
    const links = [...(container?.querySelectorAll('a[href]') || [])];
    const enclosing = container?.closest('a[href]');
    if (enclosing) links.unshift(enclosing);
    for (const link of links) {
      const term = link.textContent.trim().replace(/\s+/g, ' ');
      if (range.intersectsNode(link) && term.length >= 3 && term.length <= 80 &&
          selection.toString().toLowerCase().includes(term.toLowerCase()) && !/^\[?\d+\]?$/.test(term)) terms.add(term);
      if (terms.size >= 20) return [...terms];
    }
  }
  return [...terms];
}

function collectMedia(kind, src) {
  const elements = [...document.querySelectorAll(kind === 'image' ? 'img' : 'video')];
  const element = elements.find(el => el.currentSrc === src || el.src === src);
  if (!element) return {text: '', media_note: 'Media tidak dapat diakses pada halaman ini.'};
  const caption = element.closest('figure')?.querySelector('figcaption')?.innerText || '';
  let subtitles = '';
  if (kind === 'video') {
    for (const track of element.textTracks || []) {
      subtitles += [...(track.activeCues || [])].map(cue => cue.text).join(' ') + ' ';
    }
  }
  const text = [element.alt, element.title, element.getAttribute('aria-label'), caption, subtitles].filter(Boolean).join(' ').slice(0, 30000);
  try {
    const width = element.naturalWidth || element.videoWidth;
    const height = element.naturalHeight || element.videoHeight;
    if (!width || !height) throw new Error('Media belum siap');
    const scale = Math.min(1, 1400 / Math.max(width, height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(width * scale); canvas.height = Math.round(height * scale);
    canvas.getContext('2d').drawImage(element, 0, 0, canvas.width, canvas.height);
    return {text, frame: canvas.toDataURL('image/jpeg', 0.85)};
  } catch {
    return {text, media_note: 'Browser membatasi pembacaan visual media ini. Scan hanya memakai caption/subtitle yang tersedia.'};
  }
}
