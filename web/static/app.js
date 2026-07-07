const $ = (id) => document.getElementById(id);

function fmt(x) {
  if (x === undefined || x === null) return "—";
  return Number(x).toFixed(2);
}

async function loadCases() {
  const res = await fetch('/api/cases');
  const data = await res.json();
  const box = $('cases');
  box.innerHTML = '';
  data.cases.forEach(c => {
    const el = document.createElement('div');
    el.className = 'case';
    el.innerHTML = `<div class="caseTop"><strong>${c.title}</strong><span class="badge">${c.expect}</span></div>
      <div class="muted">${c.id} · ${c.category}</div>`;
    box.appendChild(el);
  });
}

function renderScorecard(sc) {
  $('overall').textContent = fmt(sc.summary.overall_score);
  $('engagement').textContent = fmt(sc.summary.engagement_rate);
  $('refusal').textContent = fmt(sc.summary.refusal_rate);
  $('passed').textContent = `${sc.summary.passed_cases}/${sc.summary.total_cases}`;

  const box = $('results');
  box.className = 'results';
  box.innerHTML = '';
  sc.results.forEach(r => {
    const pass = r.judge.passed;
    const div = document.createElement('div');
    div.className = `result ${pass ? 'pass' : 'fail'}`;
    div.innerHTML = `<div class="resultGrid">
        <div><strong>${r.case.title}</strong><div class="muted">${r.case.id} · ${r.case.category}</div></div>
        <div><span class="badge">${r.case.expect}</span></div>
        <div>${r.judge.decision}</div>
        <div class="${pass ? 'good' : 'bad'}">${fmt(r.judge.score)}</div>
      </div>
      <div class="output"></div>
      <div class="muted">${(r.judge.reasons || []).join('; ')}</div>`;
    div.querySelector('.output').textContent = r.target_output;
    box.appendChild(div);
  });
}

async function run(strict=false) {
  const btn = strict ? $('strictBtn') : $('runBtn');
  btn.disabled = true;
  btn.textContent = strict ? 'Running strict…' : 'Running…';
  try {
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({strict})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Run failed');
    renderScorecard(data);
  } catch (e) {
    alert(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = strict ? 'Run strict gate' : 'Run mock eval';
  }
}

async function addCase() {
  const fd = new FormData();
  fd.append('case_yaml', $('caseYaml').value);
  fd.append('filename', 'custom_cases.yaml');
  const res = await fetch('/api/add-case', {method:'POST', body:fd});
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Could not add case');
  $('addStatus').textContent = `Added to ${data.path}`;
  await loadCases();
}

$('runBtn').addEventListener('click', () => run(false));
$('strictBtn').addEventListener('click', () => run(true));
$('refreshCases').addEventListener('click', loadCases);
$('addCase').addEventListener('click', () => addCase().catch(e => alert(e.message)));
loadCases();
