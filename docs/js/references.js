async function fetchJson(path){
  const res = await fetch(path, { cache: 'no-store' });
  if(!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  return await res.json();
}

function el(tag, attrs={}, text=null){
  const n = document.createElement(tag);
  for(const [k,v] of Object.entries(attrs)) n.setAttribute(k, v);
  if(text !== null) n.textContent = text;
  return n;
}

function renderTable(containerId, rows, columns){
  const wrap = document.getElementById(containerId);
  wrap.innerHTML = '';
  const table = el('table');
  const thead = el('thead');
  const trh = el('tr');
  for(const c of columns){ trh.appendChild(el('th', {}, c.label)); }
  thead.appendChild(trh);
  table.appendChild(thead);

  const tbody = el('tbody');
  for(const r of rows){
    const tr = el('tr');
    for(const c of columns){
      const val = (typeof c.get === 'function') ? c.get(r) : r[c.key];
      const td = el('td');
      td.textContent = (val === undefined || val === null || val === '') ? '—' : String(val);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
}

function setStatus(text, ok=true){
  const s = document.getElementById('status');
  s.textContent = text;
  s.style.color = ok ? 'var(--muted)' : 'var(--danger)';
}

(async () => {
  try{
    setStatus('Loading references…');
    const ref = await fetchJson('./data/references.json');

    renderTable('presets', ref.presets ?? [], [
      {key:'name', label:'Preset'},
      {key:'dataset_id', label:'Dataset ID'},
      {key:'kind', label:'Kind'},
      {key:'notes', label:'Notes'},
    ]);

    renderTable('categories', ref.offense_categories ?? [], [
      {key:'category', label:'Category'},
      {key:'keyword_count', label:'Keywords'},
      {key:'type_count', label:'Mapped offense types'},
    ]);

    // Flatten offense types for table
    const types = [];
    for(const item of (ref.offense_type_map ?? [])){
      for(const off of item.offense_types ?? []){
        types.push({ category: item.category, offense: off });
      }
    }

    renderTable('offenseTypes', types, [
      {key:'category', label:'Category'},
      {key:'offense', label:'offincident string'},
    ]);

    setStatus('OK');
  }catch(e){
    console.error(e);
    setStatus(`Error: ${e.message}`, false);
  }
})();
