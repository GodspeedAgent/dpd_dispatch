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

function popupHtml(p){
  const rows = [
    ['Date', p.date1],
    ['Offense', p.offincident],
    ['Beat', p.beat],
    ['Division', p.division],
    ['Address', p.incident_address],
    ['Incident #', p.incidentnum],
  ];
  return `
    <div style="font-family: ui-monospace, Menlo, monospace; font-size:12px; line-height:1.25;">
      ${rows.map(([k,v]) => `<div><b>${k}:</b> ${(v ?? '—')}</div>`).join('')}
    </div>
  `;
}

(async () => {
  try{
    setStatus('Loading…');

    // Base map (Dallas-ish)
    const map = L.map('map', { preferCanvas: true }).setView([32.7767, -96.7970], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    const geo = await fetchJson('./data/historical_snapshot.geojson');
    const allFeatures = geo?.features ?? [];

    const beatEl = document.getElementById('vBeat');
    const divEl = document.getElementById('vDivision');
    const textEl = document.getElementById('vText');
    const summaryEl = document.getElementById('vSummary');

    let layer = null;

    function matches(f){
      const p = f.properties ?? {};
      const beatQ = norm(beatEl?.value);
      const divQ = norm(divEl?.value);
      const textQ = norm(textEl?.value);

      if(beatQ && norm(p.beat) !== beatQ) return false;
      if(divQ && !norm(p.division).includes(divQ)) return false;
      if(textQ){
        const hay = `${norm(p.offincident)} ${norm(p.incident_address)}`;
        if(!hay.includes(textQ)) return false;
      }
      return true;
    }

    function render(){
      const filtered = allFeatures.filter(matches);

      if(layer){
        layer.remove();
      }

      layer = L.geoJSON(filtered, {
        pointToLayer: (feature, latlng) => L.circleMarker(latlng, {
          radius: 5,
          weight: 1,
          color: 'rgba(99,167,255,.9)',
          fillColor: 'rgba(69,240,198,.35)',
          fillOpacity: 0.8,
        }),
        onEachFeature: (feature, l) => {
          l.bindPopup(popupHtml(feature.properties ?? {}));
        }
      }).addTo(map);

      if(summaryEl){
        summaryEl.textContent = `Showing ${filtered.length} of ${allFeatures.length} points` +
          (beatEl?.value ? ` | beat=${beatEl.value}` : '') +
          (divEl?.value ? ` | division~="${divEl.value}"` : '') +
          (textEl?.value ? ` | text~="${textEl.value}"` : '');
      }

      if(filtered.length > 0){
        try{
          map.fitBounds(layer.getBounds().pad(0.15));
        }catch(e){/* ignore */}
      }
    }

    beatEl?.addEventListener('input', render);
    divEl?.addEventListener('input', render);
    textEl?.addEventListener('input', render);
    document.getElementById('vClear')?.addEventListener('click', () => {
      beatEl.value = '';
      divEl.value = '';
      textEl.value = '';
      render();
    });

    render();

    setStatus('OK');
  }catch(e){
    console.error(e);
    setStatus(`Error: ${e.message}`, false);
    const summaryEl = document.getElementById('vSummary');
    if(summaryEl) summaryEl.textContent = 'Map unavailable: generate historical_snapshot.geojson first.';
  }
})();
