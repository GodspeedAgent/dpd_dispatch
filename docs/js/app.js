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

function renderTable(container, rows, columns){
  const wrap = document.getElementById(container);
  wrap.innerHTML = '';
  const table = el('table');
  const thead = el('thead');
  const trh = el('tr');
  for(const c of columns){
    trh.appendChild(el('th', {}, c.label));
  }
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
    setStatus('Loading data…');
    const snapshot = await fetchJson('./data/active_calls_snapshot.json');

    document.getElementById('totalCalls').textContent = snapshot?.summary?.total_calls ?? '—';
    document.getElementById('updatedAt').textContent = snapshot?.summary?.generated_at ?? '—';

    renderTable('byRegionBeat', snapshot.by_region_beat ?? [], [
      { key:'region', label:'Region' },
      { key:'beat', label:'Beat' },
      { key:'count', label:'Calls' },
    ]);

    renderTable('rawCalls', (snapshot.calls ?? []).slice(0,200), [
      { key:'call_number', label:'Call #' },
      { key:'nature', label:'Nature' },
      { key:'beat', label:'Beat' },
      { key:'address', label:'Address' },
      { key:'time', label:'Time' },
    ]);

    // Historical snapshot
    try{
      const hist = await fetchJson('./data/historical_snapshot.json');
      document.getElementById('histTitle').textContent = `Historical (last ${hist?.summary?.days ?? '—'} days): ${hist?.summary?.title ?? ''}`;
      document.getElementById('histTotal').textContent = hist?.summary?.total_incidents ?? '—';
      document.getElementById('histGenerated').textContent = hist?.summary?.generated_at ?? '—';

      renderTable('histTopBeats', hist.top_beats ?? [], [
        { key:'beat', label:'Beat' },
        { key:'count', label:'Incidents' },
      ]);
      renderTable('histTopOffenses', hist.top_offenses ?? [], [
        { key:'offincident', label:'offincident' },
        { key:'count', label:'Count' },
      ]);
      renderTable('histRows', (hist.incidents ?? []).slice(0,200), [
        { key:'date1', label:'Date' },
        { key:'incidentnum', label:'Incident #' },
        { key:'offincident', label:'Offense' },
        { key:'beat', label:'Beat' },
        { key:'division', label:'Division' },
        { key:'incident_address', label:'Address' },
      ]);
    }catch(e){
      // If file isn't present yet, don't fail the whole page.
      console.warn('historical_snapshot.json not available', e);
    }

    setStatus('OK');
  }catch(e){
    console.error(e);
    setStatus(`Error: ${e.message}`, false);
  }
})();
