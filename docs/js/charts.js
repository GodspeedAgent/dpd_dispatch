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

    const gate = document.getElementById('chartGate');

    // Historical snapshot (optional)
    try{
      const hist = await fetchJson('./data/historical_snapshot.json');

      const days = hist?.summary?.days;
      const beat = hist?.summary?.beat;

      // Render charts ONLY if scoped:
      // - beat is specified OR
      // - days is reasonably short (<= 14)
      const scoped = Boolean((beat && String(beat).trim() !== '') || (typeof days === 'number' && days <= 14));

      if(!scoped){
        if(gate){
          gate.textContent = `Charts paused: snapshot too broad (beat not set; days=${days ?? '—'}).`;
        }
        setStatus('OK');
        return;
      }

      if(gate){
        gate.textContent = `Charts on: ${beat ? `beat=${beat}` : ''}${(beat && days) ? ' | ' : ''}${days ? `days=${days}` : ''}`.trim();
      }

      // Show sections
      document.getElementById('histBeatsSection').style.display = '';
      document.getElementById('histOffensesSection').style.display = '';

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
      if(gate){
        gate.textContent = 'Charts paused: no historical snapshot yet.';
      }
    }

    setStatus('OK');
  }catch(e){
    console.error(e);
    setStatus(`Error: ${e.message}`, false);
  }
})();
