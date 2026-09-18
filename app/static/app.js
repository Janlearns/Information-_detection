let mode = 'url', output;
const $ = id => document.getElementById(id);
document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => {
  mode = button.dataset.mode;
  document.querySelectorAll('[data-mode]').forEach(b => b.classList.toggle('active', b === button));
  $('url-fields').hidden = mode !== 'url'; $('text-fields').hidden = mode !== 'text';
  $('url').required = mode === 'url'; $('text').required = mode === 'text';
}));
function node(tag, text, cls) { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; }
$('form').addEventListener('submit', async event => {
  event.preventDefault(); $('submit').disabled = true; $('results').replaceChildren(); $('download').hidden = true;
  $('status').textContent = 'Mengambil dan menganalisis artikel… Unduhan model pertama dapat memerlukan beberapa menit.';
  try {
    const response = await fetch('/api/analyze', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(mode === 'url' ? {url:$('url').value, max_pages:Number($('pages').value)} : {text:$('text').value})});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
    output = data; $('status').textContent = `${data.articles.length} artikel dianalisis. ${data.errors.length} halaman tidak dapat diproses.`;
    for (const item of data.articles) {
      const card = node('article', '', 'card'), a = item.analysis;
      card.append(node('span', a.label, 'verdict'), node('h2', item.title));
      if (item.url) { const link = node('a', 'Buka sumber asli ↗'); link.href = item.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; card.append(link); }
      for (const [label, value] of Object.entries(a.scores)) { const row = node('div', '', 'score'); const bar = document.createElement('progress'); bar.max=1; bar.value=value; bar.setAttribute('aria-label', label); row.append(node('span', label), node('strong', `${(value*100).toFixed(1)}%`), bar); card.append(row); }
      card.append(node('p', a.warning, 'note'), node('p', a.reason, 'note'), node('p', `Model: ${a.model} · ${a.tokens_analyzed}/${a.tokens_total} token${a.truncated || item.extraction_truncated ? ' · Artikel dipotong; sebagian isi belum dianalisis.' : ''}`, 'note'));
      const details = node('details',''); details.append(node('summary','Lihat teks hasil ekstraksi'),node('p',item.text,'excerpt')); card.append(details); $('results').append(card);
    }
    for (const err of data.errors) $('results').append(node('p', `${err.url}: ${err.error}`, 'error'));
    $('download').hidden = false;
  } catch (error) { $('status').textContent = `Analisis gagal: ${error.message}`; }
  finally { $('submit').disabled = false; }
});
$('download').addEventListener('click', () => { const url = URL.createObjectURL(new Blob([JSON.stringify(output,null,2)],{type:'application/json'})); const link = document.createElement('a'); link.href=url; link.download='cekfakta-hasil.json'; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000); });
