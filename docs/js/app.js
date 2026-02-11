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

function normalize(s){
  return (s ?? '').toString().trim().toLowerCase();
}

function wireInput(id, fn){
  const n = document.getElementById(id);
  if(!n) return;
  n.addEventListener('input', fn);
  n.addEventListener('change', fn);
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

    const allCalls = snapshot.calls ?? [];

    function renderActiveFiltered(){
      const beat = normalize(document.getElementById('activeBeat')?.value);
      const nature = normalize(document.getElementById('activeNature')?.value);
      const limit = parseInt(document.getElementById('activeLimit')?.value ?? '200', 10);

      let rows = allCalls;
      if(beat){
        rows = rows.filter(r => normalize(r.beat) === beat);
      }
      if(nature){
        rows = rows.filter(r => normalize(r.nature).includes(nature));
      }

      const summary = document.getElementById('activeFilterSummary');
      if(summary){
        summary.textContent = `Filtered: ${rows.length} of ${allCalls.length} calls` +
          (beat ? ` | beat=${beat}` : '') +
          (nature ? ` | nature~="${nature}"` : '') +
          ` | showing ${Math.min(limit, rows.length)}`;
      }

      renderTable('rawCalls', rows.slice(0, limit), [
        { key:'call_number', label:'Call #' },
        { key:'nature', label:'Nature' },
        { key:'beat', label:'Beat' },
        { key:'address', label:'Address' },
        { key:'time', label:'Time' },
      ]);
    }

    wireInput('activeBeat', renderActiveFiltered);
    wireInput('activeNature', renderActiveFiltered);
    wireInput('activeLimit', renderActiveFiltered);
    document.getElementById('activeClear')?.addEventListener('click', () => {
      document.getElementById('activeBeat').value = '';
      document.getElementById('activeNature').value = '';
      document.getElementById('activeLimit').value = '200';
      renderActiveFiltered();
    });

    renderActiveFiltered();

    // Historical snapshot
    try{
      const hist = await fetchJson('./data/historical_snapshot.json');
      document.getElementById('histTitle').textContent = `Historical (last ${hist?.summary?.days ?? '—'} days): ${hist?.summary?.title ?? ''}`;
      document.getElementById('histTotal').textContent = hist?.summary?.total_incidents ?? '—';
      document.getElementById('histGenerated').textContent = hist?.summary?.generated_at ?? '—';

      const allHist = hist.incidents ?? [];

      function renderHistFiltered(){
        const beat = normalize(document.getElementById('histBeat')?.value);
        const div = normalize(document.getElementById('histDivision')?.value);
        const text = normalize(document.getElementById('histText')?.value);
        const limit = parseInt(document.getElementById('histLimit')?.value ?? '200', 10);

        let rows = allHist;
        if(beat){
          rows = rows.filter(r => normalize(r.beat) === beat);
        }
        if(div){
          rows = rows.filter(r => normalize(r.division).includes(div));
        }
        if(text){
          rows = rows.filter(r => (normalize(r.offincident) + ' ' + normalize(r.incident_address)).includes(text));
        }

        const summary = document.getElementById('histFilterSummary');
        if(summary){
          summary.textContent = `Filtered: ${rows.length} of ${allHist.length} incidents` +
            (beat ? ` | beat=${beat}` : '') +
            (div ? ` | division~="${div}"` : '') +
            (text ? ` | text~="${text}"` : '') +
            ` | showing ${Math.min(limit, rows.length)}`;
        }

        renderTable('histRows', rows.slice(0, limit), [
          { key:'date1', label:'Date' },
          { key:'incidentnum', label:'Incident #' },
          { key:'offincident', label:'Offense' },
          { key:'beat', label:'Beat' },
          { key:'division', label:'Division' },
          { key:'incident_address', label:'Address' },
        ]);

        // Recompute top tables from filtered set
        const beatCounts = {};
        const offCounts = {};
        for(const r of rows){
          const b = (r.beat ?? '').toString();
          const o = (r.offincident ?? '').toString();
          if(b) beatCounts[b] = (beatCounts[b] ?? 0) + 1;
          if(o) offCounts[o] = (offCounts[o] ?? 0) + 1;
        }
        const topBeats = Object.entries(beatCounts)
          .map(([beat,count]) => ({beat, count}))
          .sort((a,b) => b.count - a.count)
          .slice(0, 50);
        const topOff = Object.entries(offCounts)
          .map(([offincident,count]) => ({offincident, count}))
          .sort((a,b) => b.count - a.count)
          .slice(0, 50);

        renderTable('histTopBeats', topBeats, [
          { key:'beat', label:'Beat' },
          { key:'count', label:'Incidents' },
        ]);
        renderTable('histTopOffenses', topOff, [
          { key:'offincident', label:'offincident' },
          { key:'count', label:'Count' },
        ]);
      }

      wireInput('histBeat', renderHistFiltered);
      wireInput('histDivision', renderHistFiltered);
      wireInput('histText', renderHistFiltered);
      wireInput('histLimit', renderHistFiltered);
      document.getElementById('histClear')?.addEventListener('click', () => {
        document.getElementById('histBeat').value = '';
        document.getElementById('histDivision').value = '';
        document.getElementById('histText').value = '';
        document.getElementById('histLimit').value = '200';
        renderHistFiltered();
      });

      renderHistFiltered();

    }catch(e){
      console.warn('historical_snapshot.json not available', e);
    }

    setStatus('OK');
  }catch(e){
    console.error(e);
    setStatus(`Error: ${e.message}`, false);
  }
})();
