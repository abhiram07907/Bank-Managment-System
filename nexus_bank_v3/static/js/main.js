/* ═══════════════════════════════════════════
   NEXUS BANK — Main JavaScript
   ═══════════════════════════════════════════ */

/* ── Auto-dismiss flash messages ── */
document.addEventListener('DOMContentLoaded', () => {
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(f => {
    setTimeout(() => {
      f.style.transition = 'opacity .5s, transform .5s';
      f.style.opacity = '0';
      f.style.transform = 'translateY(-8px)';
      setTimeout(() => f.remove(), 500);
    }, 4000);
  });

  /* ── Active nav link highlight ── */
  const path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(a => {
    if (a.getAttribute('href') === path) a.classList.add('on');
  });

  /* ── PIN input: numbers only ── */
  document.querySelectorAll('input[name="pin"], input[name="pin2"], input[name="old_pin"], input[name="new_pin"], input[name="confirm_pin"]').forEach(el => {
    el.addEventListener('input', () => {
      el.value = el.value.replace(/\D/g, '').slice(0, 4);
    });
  });

  /* ── Account number uppercase ── */
  document.querySelectorAll('input[name="account_no"], input[name="to_account"], input[name="ben_acc"]').forEach(el => {
    el.addEventListener('input', () => { el.value = el.value.toUpperCase(); });
  });

  /* ── Phone number: digits only ── */
  const phone = document.querySelector('input[name="phone"]');
  if (phone) {
    phone.addEventListener('input', () => {
      phone.value = phone.value.replace(/\D/g, '').slice(0, 10);
    });
  }

  /* ── Amount: format preview ── */
  const amtInputs = document.querySelectorAll('input[name="amount"]');
  amtInputs.forEach(inp => {
    inp.addEventListener('blur', () => {
      const v = parseFloat(inp.value);
      if (!isNaN(v)) inp.dataset.formatted = '₹' + v.toLocaleString('en-IN', { minimumFractionDigits: 2 });
    });
  });

  /* ── Confirm dangerous actions ── */
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', e => {
      if (!confirm(btn.dataset.confirm)) e.preventDefault();
    });
  });

  /* ── Smooth card hover ripple ── */
  document.querySelectorAll('.qa').forEach(card => {
    card.addEventListener('mouseenter', function() {
      this.style.transition = 'all .22s cubic-bezier(.34,1.56,.64,1)';
    });
  });
});

/* ── EMI Calculator (loans page) ── */
function liveEMI() {
  const p   = parseFloat(document.getElementById('principal')?.value);
  const n   = parseInt(document.getElementById('tenure')?.value);
  const sel = document.getElementById('loan_type');
  if (!sel) return;
  const r = parseFloat(sel.options[sel.selectedIndex]?.dataset?.rate || 0) / (12 * 100);
  const preview = document.getElementById('emi-preview');
  if (!p || !n || p <= 0 || n <= 0) { if (preview) preview.style.display = 'none'; return; }
  const emi     = r === 0 ? p / n : p * r * Math.pow(1+r,n) / (Math.pow(1+r,n) - 1);
  const total   = emi * n;
  const interest = total - p;
  const emiEl   = document.getElementById('emi-val');
  const totEl   = document.getElementById('total-val');
  const intEl   = document.getElementById('int-val');
  if (emiEl)   emiEl.textContent   = '₹' + emi.toFixed(2);
  if (totEl)   totEl.textContent   = '₹' + total.toFixed(2);
  if (intEl)   intEl.textContent   = '₹' + interest.toFixed(2);
  if (preview) preview.style.display = 'block';
}

function updateLoanInfo() {
  const sel = document.getElementById('loan_type');
  if (!sel) return;
  const opt  = sel.options[sel.selectedIndex];
  const r    = opt?.dataset?.rate;
  const mx   = parseInt(opt?.dataset?.max || 0).toLocaleString('en-IN');
  const mn   = opt?.dataset?.min;
  const mxt  = opt?.dataset?.maxT;
  const info = document.getElementById('loan-info');
  if (info) info.innerHTML = `Rate: <strong>${r}% p.a.</strong> &nbsp;|&nbsp; Max: <strong>₹${mx}</strong> &nbsp;|&nbsp; Tenure: <strong>${mn}–${mxt} months</strong>`;
  liveEMI();
}

/* ── FD Calculator (fixed_deposits page) ── */
function calcFD() {
  const p       = parseFloat(document.getElementById('fd_amt')?.value);
  const t       = parseInt(document.getElementById('fd_tenure')?.value);
  const preview = document.getElementById('fd-preview');
  if (!p || !t) { if (preview) preview.style.display = 'none'; return; }
  const fdRatesEl = document.getElementById('fd_tenure');
  const rate  = parseFloat(fdRatesEl?.options[fdRatesEl.selectedIndex]?.dataset?.rate || 7);
  const mat   = p * (1 + rate / 100 * t / 12);
  const interest = mat - p;
  const pEl   = document.getElementById('fd-p');
  const iEl   = document.getElementById('fd-int');
  const mEl   = document.getElementById('fd-mat');
  if (pEl) pEl.textContent = '₹' + p.toLocaleString('en-IN', { minimumFractionDigits: 2 });
  if (iEl) iEl.textContent = '₹' + interest.toFixed(2);
  if (mEl) mEl.textContent = '₹' + mat.toFixed(2);
  if (preview) preview.style.display = 'block';
}

/* ── EMI Calculator page ── */
function updateRate() {
  const v    = document.getElementById('c_type')?.value;
  const rInp = document.getElementById('c_rate');
  if (rInp && v && v !== 'custom') rInp.value = v;
  calculate();
}

function calculate() {
  const p   = parseFloat(document.getElementById('c_principal')?.value);
  const n   = parseInt(document.getElementById('c_tenure')?.value);
  const r   = parseFloat(document.getElementById('c_rate')?.value) / (12 * 100);
  const res = document.getElementById('calc-result');
  if (!p || !n || isNaN(r)) { if (res) res.style.display = 'none'; return; }
  const emi      = r === 0 ? p / n : p * r * Math.pow(1+r,n) / (Math.pow(1+r,n) - 1);
  const total    = emi * n;
  const interest = total - p;
  const pPct     = Math.round(p / total * 100);
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('r-emi',   '₹' + emi.toFixed(2));
  set('r-total', '₹' + total.toFixed(2));
  set('r-int',   '₹' + interest.toFixed(2));
  set('r-ppct',  pPct + '% principal · ' + (100 - pPct) + '% interest');
  const prog = document.getElementById('r-prog');
  if (prog) prog.style.width = pPct + '%';
  if (res) res.style.display = 'block';
}

/* ── Admin tabs ── */
function showTab(name) {
  const panels = ['customers', 'transactions', 'loans', 'tickets'];
  document.querySelectorAll('.tab').forEach((t, i) => {
    const active = panels[i] === name;
    t.classList.toggle('active', active);
    const panel = document.getElementById('tab-' + panels[i]);
    if (panel) panel.classList.toggle('active', active);
  });
}

/* ── Number formatting helper ── */
function formatINR(n) {
  return '₹' + parseFloat(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
