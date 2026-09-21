(() => {
  if (globalThis.__cekFaktaPopup) return;
  globalThis.__cekFaktaPopup = true;
  let current;
  const host = document.createElement('div');
  host.style.cssText = 'all:initial;position:fixed;right:20px;bottom:20px;z-index:2147483647;';
  const root = host.attachShadow({mode: 'closed'});
  const style = document.createElement('style');
  style.textContent = `:host{color-scheme:light}section{box-sizing:border-box;width:min(390px,calc(100vw - 40px));max-height:75vh;overflow:auto;background:#fff;color:#18352c;border:1px solid #cbded5;border-radius:16px;box-shadow:0 12px 48px #0003;padding:20px;font:14px/1.55 system-ui}header{display:flex;align-items:center;justify-content:space-between;font-weight:750;color:#08794e}button{cursor:pointer;border:0;background:#edf4f0;border-radius:8px;padding:7px 10px;color:#18352c}h3{font-size:16px;margin:16px 0 6px}p{margin:8px 0;white-space:pre-wrap;overflow-wrap:anywhere}a{color:#08794e}article{border-top:1px solid #e1ebe6;padding-top:10px;margin-top:12px}.muted{color:#66766e;font-size:12px}`;
  root.append(style);
  const panel = document.createElement('section');
  panel.setAttribute('role', 'status'); panel.setAttribute('aria-live', 'polite');
  root.append(panel);
  function node(tag, text, parent = panel) {
    const el = document.createElement(tag); el.textContent = text; parent.append(el); return el;
  }
  function consensusView(consensus, parent = panel) {
    node('p', consensus.status, parent);
    for (const [label, value] of Object.entries(consensus.scores || {})) {
      node('p', `Kesepakatan ${label.toLowerCase()}: ${(value * 100).toFixed(1)}%`, parent);
    }
    node('p', consensus.coverage, parent);
    node('p', consensus.note, parent).className = 'muted';
  }
  function reset() {
    if (!host.isConnected) document.documentElement.append(host);
    host.style.display = 'block'; panel.replaceChildren();
    const header = node('header', 'CekFakta • Scan');
    const close = node('button', 'Tutup', header);
    close.onclick = () => { host.style.display = 'none'; current = null; };
  }
  chrome.runtime.onMessage.addListener(message => {
    if (message.type === 'scan-start') {
      current = message.id; reset(); node('h3', 'Sedang memeriksa…');
      node('p', 'Membaca pilihan dan mencari sumber. Proses dapat memerlukan beberapa menit.'); return;
    }
    if (message.id !== current) return;
    if (message.type === 'scan-error') { reset(); node('h3', 'Scan belum berhasil'); node('p', message.message); return; }
    if (message.type !== 'scan-result') return;
    reset(); const result = message.result;
    node('h3', result.analysis?.label || 'Persentase hubungan bukti');
    if (result.analysis?.consensus) {
      if (result.analysis.summary) node('p', result.analysis.summary);
      consensusView(result.analysis.consensus);
    } else if (result.analysis?.scores) {
      if (result.analysis.summary) node('p', result.analysis.summary);
      for (const [label, value] of Object.entries(result.analysis.scores)) {
        node('p', `${label}: ${(value * 100).toFixed(1)}%`);
        const bar = node('progress', '');
        bar.max = 1; bar.value = value; bar.style.width = '100%';
        bar.setAttribute('aria-label', label);
      }
      node('p', result.analysis.reason);
      node('p', result.analysis.warning).className = 'muted';
      if (result.analysis.truncated) node('p', 'Teks panjang: persentase hanya mencakup bagian teks yang dianalisis model.').className = 'muted';
    } else {
      node('p', result.analysis_error || 'Persentase hubungan bukti belum tersedia.');
    }
    node('h3', result.label); node('p', result.text); node('p', result.reason);
    for (const [index, statement] of (result.analysis?.statements || []).entries()) {
      const detail = node('details', '');
      node('summary', `Kalimat ${index + 1}: ${statement.text}`, detail);
      if (statement.consensus) {
        consensusView(statement.consensus, detail);
      } else {
        for (const [label, value] of Object.entries(statement.scores)) {
          node('p', `${label}: ${(value * 100).toFixed(1)}%`, detail);
        }
      }
      for (const comparison of statement.comparisons || []) {
        const url = new URL(comparison.url);
        if (!['http:', 'https:'].includes(url.protocol)) continue;
        const link = node('a', 'Sumber', detail);
        link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
        if (comparison.explanation) node('p', comparison.explanation, detail);
        for (const [label, value] of Object.entries(comparison.scores)) {
          node('p', `${label}: ${(value * 100).toFixed(1)}%`, detail);
        }
      }
    }
    if (result.selection?.candidates?.length) {
      const selection = node('details', '');
      node('summary', 'Seleksi relevansi sebelum crawling', selection);
      for (const candidate of result.selection.candidates) {
        node('p', `${candidate.selected ? (candidate.read_status === 'read' ? 'Terbaca' : 'Dicoba') : 'Dilewati'}: ${candidate.title || candidate.url}\n${candidate.reason}`, selection);
      }
    }
    for (const term of result.terms || []) { node('h3', term.term); node('p', term.meaning); }
    node('h3', 'Sumber & kutipan');
    if (!result.sources.length) node('p', 'Belum ada sumber yang berhasil dibaca.');
    for (const source of result.sources) {
      const article = node('article', '');
      const url = new URL(source.url);
      if (!['https:', 'http:'].includes(url.protocol)) continue;
      const link = node('a', source.title, article);
      link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
      node('p', source.purpose, article).className = 'muted';
      node('p', source.excerpt, article);
      const comparison = result.analysis?.comparisons?.find(item => item.url === source.url);
      if (comparison) {
        if (comparison.explanation) node('p', comparison.explanation, article);
        for (const fact of comparison.facts || []) node('p', `Kutipan angka: ${fact.quote}`, article);
        node('p', `Selesai dianalisis: ${comparison.characters_analyzed || source.characters_read || 0} karakter teks artikel.`, article).className = 'muted';
        for (const [label, value] of Object.entries(comparison.scores)) {
          node('p', `${label}: ${(value * 100).toFixed(1)}%`, article).className = 'muted';
        }
      }
      if (source.text) {
        const full = node('details', '', article);
        node('summary', 'Baca seluruh teks artikel', full);
        node('p', source.text, full);
      }
    }
    if (result.limitation) node('p', result.limitation).className = 'muted';
    if (result.errors?.length) {
      const details = node('details', '');
      node('summary', 'Catatan pencarian dan akses', details);
      for (const error of result.errors) node('p', error, details).className = 'muted';
    }
  });
})();
