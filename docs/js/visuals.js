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

function norm(s){
  return (s ?? '').toString().trim().toLowerCase();
}

function fmtChicago(iso){
  if(!iso) return '—';
  try{
    const d = new Date(iso);
    return new Intl.DateTimeFormat('en-US', {
      timeZone: 'America/Chicago',
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
      hour12: false,
      timeZoneName: 'short'
    }).format(d);
  }catch(e){
    return String(iso);
  }
}

function fmtDay(s){
  if(!s) return '—';
  const str = String(s);
  const iso = str.slice(0, 10);
  if(/\d{4}-\d{2}-\d{2}/.test(iso)) return iso;
  return str;
}

function humanizeOffense(s){
  if(!s) return '—';
  let t = String(s).trim();
  if(t === 'BMV') t = 'Burglary of Motor Vehicle';
  t = t.replace(/\(ATT\)/g, '(Attempt)');
  t = t.replace(/\s-\sATTEMPT\b/g, ' (Attempt)');
  t = t.replace(/\s-\s/g, ': ');
  t = t.replace(/\s{2,}/g, ' ');
  const keep = new Set(['DWI','UCR','NIBRS','ID','PC']);
  t = t.split(' ').map(w => {
    const up = w.toUpperCase();
    if(keep.has(up)) return up;
    if(/^[A-Z0-9]{2,}$/.test(w) && /\d/.test(w)) return w;
    return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
  }).join(' ');
  return t;
}

function isVeryViolent(p){
  const off = norm(p?.offincident);
  const nibrsCrime = norm(p?.nibrs_crime);
  // Heuristic highlight list: shootings / gunfire / murder / agg assault
  const violentKeywords = [
    'shoot', 'shots fired', 'firearm', 'gun',
    'murder', 'homicide',
    'assault (agg)', 'aggravated assault',
    'deadly weapon',
  ];
  const hay = `${off} ${nibrsCrime}`;
  return violentKeywords.some(k => hay.includes(k));
}

function popupHtml(p){
  const rows = [
    ['Date', fmtDay(p.date1)],
    ['Offense', humanizeOffense(p.offincident_label ?? p.offincident)],
    ['Beat', p.beat],
    ['Division', p.division],
    ['ZIP', p.zip_code],
    ['Address', p.incident_address],
    ['Incident #', p.incidentnum],
  ];
  return `
    <div style="font-family: ui-monospace, Menlo, monospace; font-size:12px; line-height:1.3;">
      ${rows.map(([k,v]) => `<div><b>${k}:</b> ${(v ?? '—')}</div>`).join('')}
    </div>
  `;
}

function chip(text){
  return `<span class="badge" style="margin-right:6px;">${text}</span>`;
}

(async () => {
  try{
    setStatus('Loading…');

    // Base map (dispatch dark style)
    const map = L.map('map', { preferCanvas: true }).setView([32.7767, -96.7970], 11);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap & Carto'
    }).addTo(map);

    const geo = await fetchJson('./data/historical_snapshot.geojson');
    const allFeatures = geo?.features ?? [];

    const scopeEl = document.getElementById('scope');
    const beatEl = document.getElementById('vBeat');
    const divEl = document.getElementById('vDivision');
    const textEl = document.getElementById('vText');
    const zipEl = document.getElementById('vZip');
    const violentEl = document.getElementById('vViolent');
    const chipsEl = document.getElementById('chips');
    const summaryEl = document.getElementById('vSummary');

    // Populate ZIP selector from data
    const zset = new Set();
    for(const f of allFeatures){
      const z = f?.properties?.zip_code;
      if(z) zset.add(String(z).trim());
    }
    const zips = Array.from(zset).sort();
    for(const z of zips){
      const opt = document.createElement('option');
      opt.value = z;
      opt.textContent = z;
      zipEl.appendChild(opt);
    }

    if(scopeEl){
      const title = geo?.title ?? 'Historical view';
      const days = geo?.days ?? '—';
      const generated = fmtChicago(geo?.generated_at);
      scopeEl.textContent = `${title} | window=${days} days | points=${allFeatures.length} | generated ${generated}`;
    }

    let layer = null;

    function matches(f){
      const p = f.properties ?? {};
      const beatQ = norm(beatEl?.value);
      const divQ = norm(divEl?.value);
      const textQ = norm(textEl?.value);
      const zipQ = (zipEl?.value ?? '').toString().trim();

      if(beatQ && norm(p.beat) !== beatQ) return false;
      if(divQ && !norm(p.division).includes(divQ)) return false;
      if(zipQ && String(p.zip_code ?? '').trim() !== zipQ) return false;
      if(textQ){
        const hay = `${norm(p.offincident)} ${norm(p.incident_address)} ${norm(p.nibrs_crime)} ${norm(p.ucr_offense)}`;
        if(!hay.includes(textQ)) return false;
      }
      return true;
    }

    function styleFor(p){
      const violentOn = (violentEl?.value ?? 'on') === 'on';
      const vv = violentOn && isVeryViolent(p);
      if(vv){
        return {
          radius: 7,
          weight: 2,
          color: 'rgba(255,80,80,.95)',
          fillColor: 'rgba(255,80,80,.55)',
          fillOpacity: 0.95,
        };
      }
      return {
        radius: 5,
        weight: 1,
        color: 'rgba(99,167,255,.85)',
        fillColor: 'rgba(69,240,198,.30)',
        fillOpacity: 0.85,
      };
    }

    function render(){
      const filtered = allFeatures.filter(matches);

      if(layer){
        layer.remove();
      }

      layer = L.geoJSON(filtered, {
        pointToLayer: (feature, latlng) => L.circleMarker(latlng, styleFor(feature.properties ?? {})),
        onEachFeature: (feature, l) => {
          l.bindPopup(popupHtml(feature.properties ?? {}));
        }
      }).addTo(map);

      // chips summary
      if(chipsEl){
        const chips = [];
        if(beatEl?.value) chips.push(chip(`beat=${beatEl.value}`));
        if(divEl?.value) chips.push(chip(`division~="${divEl.value}"`));
        if(zipEl?.value) chips.push(chip(`zip=${zipEl.value}`));
        if(textEl?.value) chips.push(chip(`text~="${textEl.value}"`));
        if((violentEl?.value ?? 'on') === 'on') chips.push(chip('violent highlight'));
        chipsEl.innerHTML = chips.join('') || '<span class="badge">no filters</span>';
      }

      if(summaryEl){
        summaryEl.textContent = `Showing ${filtered.length} of ${allFeatures.length} points`;
      }

      if(filtered.length > 0){
        try{
          const b = layer.getBounds();
          map.fitBounds(b.pad(0.15), { maxZoom: 14 });
        }catch(e){/* ignore */}
      }
    }

    const onChange = () => render();
    beatEl?.addEventListener('input', onChange);
    divEl?.addEventListener('input', onChange);
    textEl?.addEventListener('input', onChange);
    zipEl?.addEventListener('change', onChange);
    violentEl?.addEventListener('change', onChange);

    document.getElementById('vClear')?.addEventListener('click', () => {
      beatEl.value = '';
      divEl.value = '';
      textEl.value = '';
      zipEl.value = '';
      violentEl.value = 'on';
      render();
    });

    render();

    setStatus('OK');
  }catch(e){
    console.error(e);
    setStatus(`Error: ${e.message}`, false);
    const summaryEl = document.getElementById('vSummary');
    if(summaryEl) summaryEl.textContent = 'Map unavailable.';
  }
})();
