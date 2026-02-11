async function fetchJson(path){
  const res = await fetch(path, { cache: 'no-store' });
  if(!res.ok) throw new Error(`HTTP ${res.status} for ${path}`);
  return await res.json();
}

function setStatus(text, ok=true){
  const s = document.getElementById('status');
  s.textContent = text;
  s.style.color = ok ? 'var(--muted)' : 'var(--danger)';
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

function normBeat(s){
  const digits = (s ?? '').toString().match(/\d+/g);
  return digits ? digits.join('') : '';
}

function qs(name){
  const u = new URL(window.location.href);
  return u.searchParams.get(name);
}

async function loadBeatProfile(beat, days){
  // Convention: docs/data/beats/<beat>.json
  const path = `./data/beats/${beat}.json`;
  const obj = await fetchJson(path);
  const key = String(days);
  const snap = obj?.windows?.[key];
  if(!snap) throw new Error(`No window ${days} days in ${path}`);
  return { obj, snap };
}

(async () => {
  try{
    setStatus('Ready');

    const beatEl = document.getElementById('beat');
    const winEl = document.getElementById('window');
    const infoEl = document.getElementById('info');

    const initialBeat = normBeat(qs('beat'));
    const initialDays = qs('days');

    if(initialBeat) beatEl.value = initialBeat;
    if(initialDays && ['7','30','90'].includes(initialDays)) winEl.value = initialDays;

    async function render(){
      const beat = normBeat(beatEl.value);
      const days = parseInt(winEl.value, 10);

      if(!beat){
        infoEl.textContent = 'Enter a beat to load a profile.';
        return;
      }

      setStatus('Loading…');

      try{
        const { obj, snap } = await loadBeatProfile(beat, days);

        infoEl.textContent = `Loaded beat ${beat} | window=${days} days | dataset=${obj?.summary?.dataset_id ?? '—'}`;
        document.getElementById('total').textContent = snap?.total_incidents ?? '—';
        document.getElementById('generated').textContent = obj?.summary?.generated_at ?? '—';

        renderTable('topOffenses', snap?.top_offenses ?? [], [
          { key: 'offincident', label: 'offincident' },
          { key: 'count', label: 'Count' },
        ]);

        renderTable('topZips', snap?.top_zips ?? [], [
          { key: 'zip', label: 'ZIP' },
          { key: 'count', label: 'Incidents' },
          { key: 'pct', label: '% of beat' },
        ]);

        renderTable('daily', snap?.daily_counts ?? [], [
          { key: 'day', label: 'Day' },
          { key: 'count', label: 'Incidents' },
        ]);

        setStatus('OK');
      }catch(e){
        console.error(e);
        infoEl.textContent = `No beat profile found for ${beat}. Ask the bot to generate it.`;
        setStatus(`Missing: ${e.message}`, false);
      }
    }

    document.getElementById('load').addEventListener('click', render);
    document.getElementById('clear').addEventListener('click', () => {
      beatEl.value = '';
      winEl.value = '30';
      infoEl.textContent = '—';
      setStatus('Ready');
    });

    // Load immediately if URL params were provided
    if(normBeat(beatEl.value)){
      await render();
    }

  }catch(e){
    console.error(e);
    setStatus(`Error: ${e.message}`, false);
  }
})();
