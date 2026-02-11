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

function fmtDate(s){
  if(!s) return '—';
  const str = String(s);
  const iso = str.slice(0, 10);
  if(/\d{4}-\d{2}-\d{2}/.test(iso)) return iso;
  return str;
}

function humanizeOffense(s){
  if(!s) return '—';
  let t = String(s).trim();

  // Expand common abbreviations
  if(t === 'BMV') t = 'Burglary of Motor Vehicle';

  t = t.replace(/\(ATT\)/g, '(Attempt)');
  t = t.replace(/\s-\sATTEMPT\b/g, ' (Attempt)');
  t = t.replace(/\s-\s/g, ': ');
  t = t.replace(/\s{2,}/g, ' ');

  // Title-case but keep a few acronyms
  const keep = new Set(['DWI','UCR','NIBRS','ID','PC']);
  t = t
    .split(' ')
    .map(w => {
      const up = w.toUpperCase();
      if(keep.has(up)) return up;
      if(/^[A-Z0-9]{2,}$/.test(w) && /\d/.test(w)) return w;
      return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
    })
    .join(' ');

  return t;
}

function normBeat(s){
  const digits = (s ?? '').toString().match(/\d+/g);
  return digits ? digits.join('') : '';
}

async function loadCurrentBeat(){
  const cur = await fetchJson('./data/beat_profile_current.json');
  const beat = (cur?.beat ?? '').toString().trim();
  if(!beat) throw new Error('No current beat set');
  return beat;
}

async function loadBeatProfile(beat, days){
  const path = `./data/beats/${beat}.json`;
  const obj = await fetchJson(path);
  const key = String(days);
  const snap = obj?.windows?.[key];
  if(!snap) throw new Error(`No ${days}-day window available for beat ${beat}`);
  return { obj, snap };
}

(async () => {
  try{
    setStatus('Ready');

    const beatEl = document.getElementById('beat');
    const winEl = document.getElementById('window');
    const infoEl = document.getElementById('info');

    // Auto-load the most recently generated beat profile
    beatEl.value = await loadCurrentBeat();

    async function render(){
      const beat = normBeat(beatEl.value);
      const days = parseInt(winEl.value, 10);

      if(!beat){
        infoEl.textContent = 'No beat has been generated yet.';
        return;
      }

      setStatus('Loading…');

      try{
        const { obj, snap } = await loadBeatProfile(beat, days);

        infoEl.textContent = `Beat ${beat} | window=${days} days`;
        document.getElementById('total').textContent = snap?.total_incidents ?? '—';
        document.getElementById('generated').textContent = fmtDate(obj?.summary?.generated_at ?? '—');

        // Narrative
        const nm = document.getElementById('narrativeMeta');
        const nt = document.getElementById('narrativeText');
        const nb = document.getElementById('narrativeBullets');

        const narrative = (days === 90) ? snap?.narrative : null;
        if(days !== 90){
          if(nm) nm.textContent = 'Narrative analysis is shown for the 90-day window only.';
          if(nt) nt.textContent = '';
          if(nb) nb.innerHTML = '';
        }else{
          if(nm) nm.textContent = narrative?.headline ?? '—';
          if(nt) nt.textContent = narrative?.text ?? '';
          if(nb){
            nb.innerHTML = '';
            const bullets = narrative?.bullets ?? [];
            if(bullets.length){
              const ul = document.createElement('ul');
              ul.style.margin = '10px 0 0 18px';
              ul.style.color = 'var(--muted)';
              for(const b of bullets){
                const li = document.createElement('li');
                li.textContent = b;
                ul.appendChild(li);
              }
              nb.appendChild(ul);
            }
          }
        }

        renderTable('topOffenses', snap?.top_offenses ?? [], [
          { key: 'offincident', label: 'Offense', get: r => (r.offincident_label ?? humanizeOffense(r.offincident)) },
          { key: 'count', label: 'Count' },
        ]);

        renderTable('topZips', snap?.top_zips ?? [], [
          { key: 'zip', label: 'ZIP' },
          { key: 'count', label: 'Incidents' },
          { key: 'pct', label: '% of beat' },
        ]);

        renderTable('daily', snap?.daily_counts ?? [], [
          { key: 'day', label: 'Day', get: r => fmtDate(r.day) },
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

    // Load immediately
    await render();

  }catch(e){
    console.error(e);
    setStatus(`Error: ${e.message}`, false);
  }
})();
