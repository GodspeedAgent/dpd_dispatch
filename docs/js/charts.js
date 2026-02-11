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

function mkBar(ctx, labels, data, label){
  return new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label,
        data,
        borderWidth: 1,
        backgroundColor: 'rgba(99,167,255,.25)',
        borderColor: 'rgba(99,167,255,.7)',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      },
      scales: {
        x: { ticks: { color: '#9bb0d0' }, grid: { color: 'rgba(155,176,208,.12)' } },
        y: { ticks: { color: '#9bb0d0' }, grid: { color: 'rgba(155,176,208,.12)' } }
      }
    }
  });
}

(async () => {
  try{
    setStatus('Loading…');

    // Active calls: by_region_beat is effectively by-beat counts
    const active = await fetchJson('./data/active_calls_snapshot.json');
    const byBeat = (active.by_region_beat ?? []).slice().sort((a,b) => (b.count ?? 0) - (a.count ?? 0)).slice(0, 15);
    mkBar(
      document.getElementById('activeTopBeats'),
      byBeat.map(x => x.beat ?? '—'),
      byBeat.map(x => x.count ?? 0),
      'Active calls'
    );

    // Historical snapshot (optional)
    try{
      const hist = await fetchJson('./data/historical_snapshot.json');

      const topBeats = (hist.top_beats ?? []).slice(0, 15);
      mkBar(
        document.getElementById('histTopBeats'),
        topBeats.map(x => x.beat ?? '—'),
        topBeats.map(x => x.count ?? 0),
        'Incidents'
      );

      const topOff = (hist.top_offenses ?? []).slice(0, 12);
      mkBar(
        document.getElementById('histTopOffenses'),
        topOff.map(x => (x.offincident ?? '—').toString().slice(0, 22)),
        topOff.map(x => x.count ?? 0),
        'Incidents'
      );

    }catch(e){
      console.warn('historical_snapshot.json not available', e);
    }

    setStatus('OK');
  }catch(e){
    console.error(e);
    setStatus(`Error: ${e.message}`, false);
  }
})();
