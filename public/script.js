/**
 * TimetableAI — Script v4.0
 * Classic UI: JS arrays for all form data, modal-based entry, new grid views
 */
'use strict';

// ── DATA STORES ───────────────────────────────────────────────────────────────
let theoryCoursesList = [
  { name: 'Mathematics',     faculty: 'Prof. Sharma', credits: 3 },
  { name: 'Physics',         faculty: 'Prof. Patel',  credits: 2 },
  { name: 'Data Structures', faculty: 'Prof. Mehta',  credits: 3 },
  { name: 'Engineering Drawing', faculty: 'Prof. Joshi', credits: 2 },
  { name: 'Communication Skills', faculty: 'Prof. Rao', credits: 1 },
];

let labCoursesList = [
  { name: 'Physics Lab',  faculty: 'Prof. Patel', lab_room: 'Physics Lab Room' },
  { name: 'CS Lab',       faculty: 'Prof. Kumar', lab_room: 'Computer Lab' },
];

let theoryRoomsList = [
  { name: 'Lecture Hall A', capacity: 80 },
  { name: 'Lecture Hall B', capacity: 80 },
  { name: 'Classroom 101',  capacity: 50 },
  { name: 'Classroom 102',  capacity: 50 },
];

let labRoomsList = [
  { name: 'Physics Lab Room', subject: 'Physics Lab' },
  { name: 'Computer Lab',     subject: 'CS Lab' },
];

let timeSlots = [
  '08:00 - 09:00',
  '09:00 - 10:00',
  '10:00 - 11:00',
  '11:00 - 12:00',
  '12:00 - 13:00',
  '13:00 - 14:00',
  '14:00 - 15:00',
  '15:00 - 16:00'
];
let batchList  = ['Batch A','Batch B','Batch C'];

let lastResult   = null;
let currentView  = 'day';
let currentEntity= null;
let fitnessChart = null;

// ── CHIP COLORS ───────────────────────────────────────────────────────────────
const CHIP_COLORS = [
  { bg:'#eff6ff', border:'#3d5af1', text:'#1e40af' },
  { bg:'#f5f3ff', border:'#7c3aed', text:'#5b21b6' },
  { bg:'#ecfdf5', border:'#059669', text:'#065f46' },
  { bg:'#fff7ed', border:'#e8a020', text:'#92400e' },
  { bg:'#fdf2f8', border:'#db2777', text:'#9d174d' },
  { bg:'#f0f9ff', border:'#0284c7', text:'#075985' },
  { bg:'#fef9c3', border:'#ca8a04', text:'#713f12' },
  { bg:'#f0fdf4', border:'#16a34a', text:'#14532d' },
];
function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) { h = ((h << 5) - h) + s.charCodeAt(i); h |= 0; }
  return Math.abs(h);
}
function chipColor(name) { return CHIP_COLORS[hashStr(name) % CHIP_COLORS.length]; }

// ── HELPERS ───────────────────────────────────────────────────────────────────
function escHtml(s) {
  return String(s||'')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function makeDeleteBtn(onclick) {
  return `<button class="btn-icon" title="Delete" onclick="${onclick}">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
  </button>`;
}
function makeEditBtn(onclick) {
  return `<button class="btn-icon btn-icon-edit" title="Edit" onclick="${onclick}">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
  </button>`;
}

// ── EXPOSE SLOT/BATCH GETTERS FOR INLINE SCRIPT ───────────────────────────────
window._getSlots = () => [...timeSlots];

// ── DAYS TOGGLE ───────────────────────────────────────────────────────────────
document.querySelectorAll('.day-toggle').forEach(btn => {
  btn.addEventListener('click', () => btn.classList.toggle('active'));
});

function getSelectedDays() {
  return Array.from(document.querySelectorAll('.day-toggle.active')).map(b => b.dataset.day);
}

// ── TIME SLOTS ────────────────────────────────────────────────────────────────
function renderSlots() {
  const c = document.getElementById('slots-container');
  if (!c) return;
  c.innerHTML = timeSlots.map(s =>
    `<span class="slot-tag">${escHtml(s)} <button onclick="removeSlot('${escHtml(s)}')" title="Remove">×</button></span>`
  ).join('');
  if (window._syncLunchDropdowns) window._syncLunchDropdowns();
}

window.removeSlot = function(slot) {
  timeSlots = timeSlots.filter(s => s !== slot);
  renderSlots();
};

window.addSlot = function() {
  const inp = document.getElementById('slot-input');
  const val = (inp.value||'').trim();
  if (!val) return;
  if (timeSlots.includes(val)) { inp.value=''; return; }
  timeSlots.push(val);
  inp.value = '';
  renderSlots();
};

document.getElementById('slot-input')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); window.addSlot(); }
});

// ── BATCHES ───────────────────────────────────────────────────────────────────
function renderBatches() {
  const c = document.getElementById('batch-tags');
  if (!c) return;
  c.innerHTML = batchList.map(b =>
    `<span class="batch-tag">${escHtml(b)} <button onclick="removeBatch('${escHtml(b)}')" title="Remove">×</button></span>`
  ).join('');
}

window.removeBatch = function(b) {
  batchList = batchList.filter(x => x !== b);
  renderBatches();
};

window.addBatch = function() {
  const inp = document.getElementById('batch-input');
  const val = (inp.value||'').trim();
  if (!val || batchList.includes(val)) { inp.value=''; return; }
  batchList.push(val);
  inp.value = '';
  renderBatches();
};

document.getElementById('batch-input')?.addEventListener('keydown', e => {
  if (e.key === 'Enter') { e.preventDefault(); window.addBatch(); }
});

// ── RENDER ITEM LISTS ─────────────────────────────────────────────────────────
function renderTheoryCourses() {
  const el = document.getElementById('theory-list');
  if (!el) return;
  el.innerHTML = theoryCoursesList.map((c, i) => `
    <div class="item-row item-theory">
      <div class="item-row-content">
        <div class="item-row-title">${escHtml(c.name)}</div>
        <div class="item-row-meta">${escHtml(c.faculty)} · ${c.credits} credit${c.credits>1?'s':''}/week</div>
      </div>
      <span class="item-row-badge badge-theory">${c.credits} hr/wk</span>
      <div class="item-row-actions">
        ${makeEditBtn(`editTheoryCourse(${i})`)}
        ${makeDeleteBtn(`deleteTheoryCourse(${i})`)}
      </div>
    </div>
  `).join('');
}

function renderLabCourses() {
  const el = document.getElementById('lab-list');
  if (!el) return;
  el.innerHTML = labCoursesList.map((c,i) => `
    <div class="item-row item-lab">
      <div class="item-row-content">
        <div class="item-row-title">${escHtml(c.name)}</div>
        <div class="item-row-meta">${escHtml(c.faculty)} · Room: ${escHtml(c.lab_room)}</div>
      </div>
      <span class="item-row-badge badge-lab">2hr / batch</span>
      <div class="item-row-actions">
        ${makeEditBtn(`editLabCourse(${i})`)}
        ${makeDeleteBtn(`deleteLabCourse(${i})`)}
      </div>
    </div>
  `).join('');
}

function renderTheoryRooms() {
  const el = document.getElementById('theory-rooms-list');
  if (!el) return;
  el.innerHTML = theoryRoomsList.map((r,i) => `
    <div class="item-row item-room">
      <div class="item-row-content">
        <div class="item-row-title">${escHtml(r.name)}</div>
        <div class="item-row-meta">Capacity: ${r.capacity} seats</div>
      </div>
      <span class="item-row-badge badge-room">${r.capacity} seats</span>
      <div class="item-row-actions">
        ${makeEditBtn(`editTheoryRoom(${i})`)}
        ${makeDeleteBtn(`deleteTheoryRoom(${i})`)}
      </div>
    </div>
  `).join('');
}

function renderLabRooms() {
  const el = document.getElementById('lab-rooms-list');
  if (!el) return;
  el.innerHTML = labRoomsList.map((r,i) => `
    <div class="item-row" style="border-left-color:var(--warning)">
      <div class="item-row-content">
        <div class="item-row-title">${escHtml(r.name)}</div>
        <div class="item-row-meta">Subject: ${escHtml(r.subject)}</div>
      </div>
      <span class="item-row-badge badge-labroom">Dedicated</span>
      <div class="item-row-actions">
        ${makeEditBtn(`editLabRoom(${i})`)}
        ${makeDeleteBtn(`deleteLabRoom(${i})`)}
      </div>
    </div>
  `).join('');
}

// ── MODAL OPEN / CLOSE ────────────────────────────────────────────────────────
window.openModal = function(type, idx) {
  idx = (idx === undefined) ? -1 : parseInt(idx);
  const overlay = document.getElementById('modal-' + type);
  if (!overlay) return;

  // Reset edit index
  const editIdx = overlay.querySelector('input[type="hidden"]');
  if (editIdx) editIdx.value = idx;

  // Prefill or clear
  if (type === 'theory') {
    const c = idx >= 0 ? theoryCoursesList[idx] : {name:'',faculty:'',credits:3};
    document.getElementById('theory-name').value    = c.name;
    document.getElementById('theory-faculty').value = c.faculty;
    document.getElementById('theory-credits').value = c.credits;
    document.getElementById('modal-theory-title').textContent = idx>=0 ? 'Edit Theory Course' : 'Add Theory Course';
  } else if (type === 'lab') {
    const c = idx >= 0 ? labCoursesList[idx] : {name:'',faculty:'',lab_room:''};
    document.getElementById('lab-name').value      = c.name;
    document.getElementById('lab-faculty').value   = c.faculty;
    document.getElementById('lab-room-name').value = c.lab_room;
    document.getElementById('modal-lab-title').textContent = idx>=0 ? 'Edit Lab Course' : 'Add Lab Course';
  } else if (type === 'theory-room') {
    const r = idx >= 0 ? theoryRoomsList[idx] : {name:'',capacity:60};
    document.getElementById('theory-room-name').value = r.name;
    document.getElementById('theory-room-cap').value  = r.capacity;
    document.getElementById('modal-theory-room-title').textContent = idx>=0 ? 'Edit Theory Room' : 'Add Theory Room';
  } else if (type === 'lab-room') {
    const r = idx >= 0 ? labRoomsList[idx] : {name:'',subject:''};
    document.getElementById('lab-room-name-field').value = r.name;
    document.getElementById('lab-room-subject').value    = r.subject;
    document.getElementById('modal-lab-room-title').textContent = idx>=0 ? 'Edit Lab Room' : 'Add Lab Room';
  }

  overlay.style.display = 'flex';
  // Focus first input
  setTimeout(() => overlay.querySelector('.form-input')?.focus(), 60);
};

window.closeModal = function(type) {
  const overlay = document.getElementById('modal-' + type);
  if (overlay) overlay.style.display = 'none';
};

// Close on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay').forEach(o => { o.style.display = 'none'; });
  }
});

// ── SAVE / DELETE ─────────────────────────────────────────────────────────────
window.saveTheoryCourse = function() {
  const name    = document.getElementById('theory-name').value.trim();
  const faculty = document.getElementById('theory-faculty').value.trim();
  const credits = parseInt(document.getElementById('theory-credits').value) || 1;
  if (!name) { document.getElementById('theory-name').focus(); return; }
  const idx = parseInt(document.getElementById('theory-edit-idx').value);
  const obj = { name, faculty, credits };
  if (idx >= 0) theoryCoursesList[idx] = obj;
  else theoryCoursesList.push(obj);
  renderTheoryCourses();
  closeModal('theory');
};

window.editTheoryCourse   = (i) => openModal('theory', i);
window.deleteTheoryCourse = (i) => { theoryCoursesList.splice(i,1); renderTheoryCourses(); };

window.saveLabCourse = function() {
  const name     = document.getElementById('lab-name').value.trim();
  const faculty  = document.getElementById('lab-faculty').value.trim();
  const lab_room = document.getElementById('lab-room-name').value.trim();
  if (!name) { document.getElementById('lab-name').focus(); return; }
  const idx = parseInt(document.getElementById('lab-edit-idx').value);
  const obj = { name, faculty, lab_room, batches: [...batchList] };
  if (idx >= 0) labCoursesList[idx] = obj;
  else labCoursesList.push(obj);
  renderLabCourses();
  closeModal('lab');
};

window.editLabCourse   = (i) => openModal('lab', i);
window.deleteLabCourse = (i) => { labCoursesList.splice(i,1); renderLabCourses(); };

window.saveTheoryRoom = function() {
  const name     = document.getElementById('theory-room-name').value.trim();
  const capacity = parseInt(document.getElementById('theory-room-cap').value) || 60;
  if (!name) { document.getElementById('theory-room-name').focus(); return; }
  const idx = parseInt(document.getElementById('theory-room-edit-idx').value);
  const obj = { name, capacity };
  if (idx >= 0) theoryRoomsList[idx] = obj;
  else theoryRoomsList.push(obj);
  renderTheoryRooms();
  closeModal('theory-room');
};

window.editTheoryRoom   = (i) => openModal('theory-room', i);
window.deleteTheoryRoom = (i) => { theoryRoomsList.splice(i,1); renderTheoryRooms(); };

window.saveLabRoom = function() {
  const name    = document.getElementById('lab-room-name-field').value.trim();
  const subject = document.getElementById('lab-room-subject').value.trim();
  if (!name) { document.getElementById('lab-room-name-field').focus(); return; }
  const idx = parseInt(document.getElementById('lab-room-edit-idx').value);
  const obj = { name, subject };
  if (idx >= 0) labRoomsList[idx] = obj;
  else labRoomsList.push(obj);
  renderLabRooms();
  closeModal('lab-room');
};

window.editLabRoom   = (i) => openModal('lab-room', i);
window.deleteLabRoom = (i) => { labRoomsList.splice(i,1); renderLabRooms(); };

// ── SAVE (Enter) IN MODALS ────────────────────────────────────────────────────
['modal-theory','modal-lab','modal-theory-room','modal-lab-room'].forEach(id => {
  document.getElementById(id)?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const saveFns = {
        'modal-theory':      'saveTheoryCourse',
        'modal-lab':         'saveLabCourse',
        'modal-theory-room': 'saveTheoryRoom',
        'modal-lab-room':    'saveLabRoom',
      };
      window[saveFns[id]]?.();
    }
  });
});

// ── BUILD CONFIG ──────────────────────────────────────────────────────────────
function buildConfig() {
  const labCoursesWithBatches = labCoursesList.map(c => ({
    ...c, batches: [...batchList],
  }));
  return {
    days:          getSelectedDays(),
    time_slots:    [...timeSlots],
    batches:       [...batchList],
    theory_courses: theoryCoursesList.map(c => ({ ...c })),
    lab_courses:    labCoursesWithBatches,
    theory_rooms:   theoryRoomsList.map(r => ({ ...r })),
    lab_rooms:      labRoomsList.map(r => ({ ...r })),
    lunch_window: {
      start_slot: document.getElementById('input-lunch-start')?.value || '',
      end_slot:   document.getElementById('input-lunch-end')?.value   || '',
    },
    prefer_theory_time: document.getElementById('input-theory-pref')?.value || 'unbiased',
    prefer_lab_time:    document.getElementById('input-lab-pref')?.value    || 'unbiased',
    population_size:    parseInt(document.getElementById('input-pop-size')?.value)         || 100,
    mutation_rate:      parseFloat(document.getElementById('input-mutation-rate')?.value)  || 0.05,
    crossover_rate:     parseFloat(document.getElementById('input-crossover-rate')?.value) || 0.80,
    max_generations:    parseInt(document.getElementById('input-max-generations')?.value)  || 500,
    nlp_constraints_text: document.getElementById('nlp-constraints-input')?.value.trim()   || '',
  };
}

// ── RUN ───────────────────────────────────────────────────────────────────────
const btnRun = document.getElementById('btn-run');

btnRun.addEventListener('click', async () => {
  if (btnRun.disabled) return;
  const days = getSelectedDays();
  if (days.length === 0) { alert('Please select at least one working day.'); return; }
  if (timeSlots.length === 0) { alert('Please add at least one time slot.'); return; }
  if (theoryCoursesList.length === 0 && labCoursesList.length === 0) {
    alert('Please add at least one course.'); return;
  }

  btnRun.disabled = true;
  btnRun.textContent = 'Generating Timetable…';

  document.getElementById('results').hidden = true;

  try {
    const config = buildConfig();
    const res = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
      throw new Error(err.error || `Server error ${res.status}`);
    }
    const data = await res.json();
    lastResult = data;
    displayResultsUI(data);
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    btnRun.disabled = false;
    btnRun.textContent = 'Generate Timetable';
  }
});

// ── DISPLAY RESULTS & UNHIDE UI ───────────────────────────────────────────────
function displayResultsUI(data) {
  const idleState = document.getElementById('idle-state');
  const skeleton  = document.getElementById('skeleton-container');
  const results   = document.getElementById('results');

  if (idleState) idleState.hidden = true;
  if (skeleton)  skeleton.hidden = true;

  // Render content
  renderResults(data);

  if (results) {
    results.hidden = false;
    // Animate every section so it is visible immediately (replaces opacity: 0)
    results.querySelectorAll('.anim-section').forEach((s, i) => {
      s.style.animationDelay = (i * 0.05) + 's';
      s.classList.add('anim-enter');
    });
    // Smooth scroll down to results
    setTimeout(() => {
      results.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
  }

  if (window.setAppState) {
    window.setAppState('done');
  }
}

// ── RENDER RESULTS ────────────────────────────────────────────────────────────
function renderResults(data) {
  document.querySelector('#stat-gen .stat-card__value').textContent         = data.generations_run ?? '—';
  document.querySelector('#stat-violations .stat-card__value').textContent  = data.violations ?? '—';
  document.querySelector('#stat-theory .stat-card__value').textContent      = data.theory_sessions ?? '—';
  document.querySelector('#stat-lab .stat-card__value').textContent         = data.lab_sessions ?? '—';

  // Violations panel
  const vPanel = document.getElementById('violations-panel');
  const vList  = document.getElementById('violations-list');
  vList.innerHTML = '';
  if (data.violations > 0 && data.violation_detail?.length) {
    vPanel.hidden = false;
    data.violation_detail.forEach(msg => {
      const li = document.createElement('li');
      li.className = 'violation-item';
      li.textContent = msg;
      vList.appendChild(li);
    });
  } else {
    vPanel.hidden = true;
  }

  renderConfigGrid(data.config);
  setupViewTabs(data);
  renderDetailTable(data.schedule);

  // NLP Soft Constraints & Edit Results
  const nlpPanel = document.getElementById('nlp-results-panel');
  const nlpList = document.getElementById('nlp-eval-list');
  const nlpRate = document.getElementById('nlp-rate-badge');
  const nlpMode = document.getElementById('nlp-mode-indicator');

  if (nlpPanel && data.nlp_results && data.nlp_results.evaluations && data.nlp_results.evaluations.length > 0) {
    nlpPanel.hidden = false;
    const rate = data.nlp_results.satisfaction_rate ?? 100;
    if (nlpRate) {
      nlpRate.textContent = `${rate}% Satisfied`;
      if (rate >= 80) {
        nlpRate.style.background = 'var(--success-lt)';
        nlpRate.style.color = 'var(--success)';
        nlpRate.style.borderColor = '#a7f3d0';
      } else {
        nlpRate.style.background = 'var(--danger-lt)';
        nlpRate.style.color = 'var(--danger)';
        nlpRate.style.borderColor = '#fecaca';
      }
    }

    if (nlpMode) {
      nlpMode.textContent = data.nlp_results.mode === 'edit'
        ? 'MODE: CSV EDIT & RE-EVOLVE'
        : 'MODE: NATURAL LANGUAGE SOFT CONSTRAINTS';
    }

    if (nlpList) {
      nlpList.innerHTML = data.nlp_results.evaluations.map(ev => {
        const isSat = ev.status === 'Satisfied';
        const badgeCls = isSat ? 'nlp-eval-status--satisfied' : 'nlp-eval-status--violated';
        const icon = isSat ? '✓' : '✗';
        const suggestionsHtml = ev.suggestions && ev.suggestions.length ? `
          <div style="margin-top:8px;padding:8px 12px;background:rgba(61,90,241,0.06);border-radius:6px;border:1px dashed var(--primary);">
            <div style="font-size:0.75rem;font-weight:700;color:var(--primary);margin-bottom:4px;">💡 Conflict-Free Available Slots (Suggestions):</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;">
              ${ev.suggestions.map(s => `<span class="badge" style="background:#fff;border:1px solid var(--primary);color:var(--primary);font-size:0.72rem;padding:2px 8px;border-radius:4px;font-weight:600;">${escHtml(s)}</span>`).join('')}
            </div>
          </div>
        ` : '';

        return `
          <div class="nlp-eval-card">
            <div style="flex:1;">
              <div style="font-weight:600;color:var(--text);display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span>${escHtml(ev.text)}</span>
              </div>
              <div style="font-size:0.76rem;color:var(--text-2);margin-top:4px;line-height:1.4;">${escHtml(ev.details || '')}</div>
              ${suggestionsHtml}
            </div>
            <span class="nlp-eval-status ${badgeCls}">${icon} ${escHtml(ev.status)}</span>
          </div>
        `;
      }).join('');
    }
  } else if (nlpPanel) {
    nlpPanel.hidden = true;
  }

  document.getElementById('results').hidden = false;
}

// ── VIEW TABS ─────────────────────────────────────────────────────────────────
function setupViewTabs(data) {
  document.querySelectorAll('.view-tab').forEach(tab => {
    // Clone to remove old listeners
    const fresh = tab.cloneNode(true);
    tab.parentNode.replaceChild(fresh, tab);
    fresh.addEventListener('click', function() {
      document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
      this.classList.add('active');
      currentView = this.getAttribute('data-view');
      let entities = [];
      if (currentView === 'day')   entities = data.days        || [];
      if (currentView === 'room')  entities = data.all_rooms   || [];
      if (currentView === 'batch') entities = data.all_batches || [];
      currentEntity = entities[0] || null;
      renderEntityPills(entities);
      renderGridForEntity(data);
    });
  });

  currentView = 'day';
  const days = data.days || [];
  currentEntity = days[0] || null;
  renderEntityPills(days);
  renderGridForEntity(data);
}

function renderEntityPills(entities) {
  const pillsEl = document.getElementById('entity-pills');
  pillsEl.innerHTML = '';
  entities.forEach((ent, i) => {
    const btn = document.createElement('button');
    btn.className = 'entity-pill' + (i === 0 ? ' active' : '');
    btn.textContent = ent;
    btn.addEventListener('click', function() {
      document.querySelectorAll('.entity-pill').forEach(p => p.classList.remove('active'));
      this.classList.add('active');
      currentEntity = ent;
      renderGridForEntity(lastResult);
    });
    pillsEl.appendChild(btn);
  });
}

// ── GRID RENDERER ─────────────────────────────────────────────────────────────
function renderGridForEntity(data) {
  const table = document.getElementById('timetable');
  table.innerHTML = '';
  const slots = data.time_slots || [];

  if (currentView === 'day') {
    const allRooms = data.all_rooms || [];
    buildGridTable(table, allRooms, slots, (room, slot) => {
      const entries = (data.grid_by_room || {})[room]?.[currentEntity]?.[slot] || [];
      return { entries };
    }, (header, isLab) => {
      const isLabRoom = (data.lab_rooms || []).includes(header);
      return header + (isLabRoom ? ' 🔬' : '');
    });

  } else if (currentView === 'room') {
    const days = data.days || [];
    buildGridTable(table, days, slots, (day, slot) => {
      const entries = (data.grid_by_room || {})[currentEntity]?.[day]?.[slot] || [];
      return { entries };
    });

  } else if (currentView === 'batch') {
    const days = data.days || [];
    buildGridTable(table, days, slots, (day, slot) => {
      const entries = (data.grid_by_batch || {})[currentEntity]?.[day]?.[slot] || [];
      return { entries };
    });
  }
}

function buildGridTable(table, colHeaders, slots, getCellData, headerLabel) {
  const thead = table.createTHead();
  const hRow  = thead.insertRow();
  addCell(hRow, 'TIME', 'th', 'th-time');
  colHeaders.forEach(h => {
    const label = headerLabel ? headerLabel(h) : h;
    addCell(hRow, label, 'th');
  });

  const tbody = table.createTBody();
  slots.forEach(slot => {
    const row = tbody.insertRow();
    addCell(row, slot, 'td', 'td-time');
    colHeaders.forEach(col => {
      const td = row.insertCell();
      const { entries } = getCellData(col, slot);
      if (!entries.length) {
        td.className = 'cell-empty';
      } else {
        entries.forEach(e => {
          if (!e.is_continuation) td.appendChild(makeChip(e));
          else td.classList.add('cell-continuation');
        });
      }
    });
  });
}

function addCell(row, text, tag, cls) {
  const el = document.createElement(tag);
  el.textContent = text;
  if (cls) el.className = cls;
  row.appendChild(el);
  return el;
}

function makeChip(entry) {
  const div  = document.createElement('div');
  const isLab = entry.type === 'lab';
  const col   = chipColor(entry.course || '');
  div.className = 'chip chip--' + (isLab ? 'lab' : 'theory');
  div.style.background   = col.bg;
  div.style.color        = col.text;
  div.style.borderColor  = col.border;

  const subLine = isLab
    ? (entry.batch || '') + ' · ' + (entry.time_label || '')
    : (entry.faculty || '') + ' · ' + (entry.time_label || '');

  div.innerHTML = `<span class="chip-name">${escHtml(entry.course)}</span>
                   <span class="chip-sub">${escHtml(subLine)}</span>`;
  if (isLab) {
    const badge = document.createElement('span');
    badge.className = 'chip-lab-badge';
    badge.textContent = 'LAB';
    div.appendChild(badge);
  }
  div.title = [
    entry.course, entry.faculty,
    'Batch: ' + (entry.batch || 'Whole Division'),
    'Room: ' + entry.room,
    entry.time_label,
  ].join('\n');
  return div;
}

// ── DETAIL TABLE ──────────────────────────────────────────────────────────────
function renderDetailTable(schedule) {
  const tbody = document.querySelector('#schedule-detail tbody');
  tbody.innerHTML = '';
  (schedule || []).forEach(e => {
    const tr = tbody.insertRow();
    const isLab = e.type === 'lab';
    tr.innerHTML = `
      <td><span class="type-badge type-badge--${isLab?'lab':'theory'}">${isLab?'Lab':'Theory'}</span></td>
      <td>${escHtml(e.course)}</td>
      <td>${escHtml(e.faculty)}</td>
      <td>${escHtml(e.batch || 'Whole Division')}</td>
      <td>${escHtml(e.day)}</td>
      <td><span style="font-family:var(--font-mono);font-size:0.78rem">${escHtml(e.time_label)}</span></td>
      <td>${escHtml(e.room)}</td>
    `;
  });
}

// ── CONFIG GRID ───────────────────────────────────────────────────────────────
function renderConfigGrid(cfg) {
  const el = document.getElementById('config-grid');
  if (!el || !cfg) return;
  const items = [
    ['Population',      cfg.population_size],
    ['Mutation',        cfg.mutation_rate],
    ['Crossover',       cfg.crossover_rate],
    ['Max Gen.',        cfg.max_generations],
    ['Days',            cfg.num_days],
    ['Slots/Day',       cfg.num_slots],
    ['Theory Rooms',    cfg.num_theory_rooms],
    ['Lab Rooms',       cfg.num_lab_rooms],
    ['Theory Pref.',    cfg.prefer_theory_time],
    ['Lab Pref.',       cfg.prefer_lab_time],
    ['Lunch Window',    (cfg.lunch_window||[]).join(' – ') || '—'],
  ];
  el.innerHTML = items.map(([k,v]) =>
    `<div class="cfg-item"><span class="cfg-key">${k}</span><span class="cfg-val">${v}</span></div>`
  ).join('');
}

// ── CONVERGENCE CHART ─────────────────────────────────────────────────────────
function renderChart(history) {
  const canvas = document.getElementById('chart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  if (fitnessChart) { fitnessChart.destroy(); fitnessChart = null; }
  if (typeof Chart !== 'undefined') {
    fitnessChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: history.map((_,i) => i),
        datasets: [{
          label: 'Best Fitness', data: history,
          borderColor: '#3d5af1', backgroundColor: 'rgba(61,90,241,0.08)',
          borderWidth: 2.5, pointRadius: 0, fill: true, tension: 0.4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color:'#9aa5b4', maxTicksLimit:10 }, grid: { color:'rgba(0,0,0,0.05)' } },
          y: { ticks: { color:'#9aa5b4' },                   grid: { color:'rgba(0,0,0,0.05)' } },
        }
      }
    });
  } else {
    drawFallbackChart(ctx, canvas, history);
  }
}

function drawFallbackChart(ctx, canvas, history) {
  const W = canvas.width  = canvas.offsetWidth  || 400;
  const H = canvas.height = canvas.offsetHeight || 220;
  ctx.clearRect(0, 0, W, H);
  if (!history || history.length < 2) return;
  const min = Math.min(...history), max = Math.max(...history);
  const range = max - min || 1, pad = 24;
  ctx.strokeStyle = '#3d5af1'; ctx.lineWidth = 2;
  ctx.beginPath();
  history.forEach((v,i) => {
    const x = pad + (i/(history.length-1))*(W-pad*2);
    const y = H - pad - ((v-min)/range)*(H-pad*2);
    i===0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y);
  });
  ctx.stroke();
  ctx.fillStyle = 'rgba(61,90,241,0.08)';
  ctx.lineTo(W-pad, H-pad); ctx.lineTo(pad, H-pad);
  ctx.closePath(); ctx.fill();
}

// ── TIME FORMAT HELPER (Prevents Excel Date Conversion e.g. 8-9 -> 08-Sep) ──
function formatSlotToTime(rawSlot) {
  if (!rawSlot) return '';
  const s = String(rawSlot).trim().replace(/[\u2013\u2014]/g, '-');
  // Check if it matches '8-9', '9-10', '1-2', '2-3', etc.
  const m = s.match(/^(\d{1,2})\s*-\s*(\d{1,2})$/);
  if (m) {
    let h1 = parseInt(m[1], 10);
    let h2 = parseInt(m[2], 10);
    // Convert 12-hr college notation (e.g. 1-2 => 13:00 - 14:00)
    const start_h = h1 >= 7 ? h1 : h1 + 12;
    const end_h   = h2 >= 7 ? h2 : h2 + 12;
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(start_h)}:00 - ${pad(end_h)}:00`;
  }
  return s;
}

// ── BUILD TIMETABLE GRID (single section) ─────────────────────────────────────
function buildGridForFilter(data, filterFn) {
  const schedule = data.schedule || [];
  const days = data.days || [];
  const slots = data.time_slots || [];
  const rows = [];

  // Header row: Time | Mon | Tue | Wed | ...
  rows.push(['Time', ...days]);

  slots.forEach(slot => {
    // Format slot as clean time (e.g. 08:00 - 09:00) so Excel treats it as text, NEVER a month
    const cleanSlot = formatSlotToTime(slot);
    const row = [cleanSlot];
    days.forEach(day => {
      const matches = schedule.filter(e =>
        filterFn(e) && e.day === day && (
          (e.time_label||'').startsWith(slot) || (e.slot||'').startsWith(slot)
        )
      );
      if (matches.length === 0) {
        row.push('—');
      } else {
        const cellParts = matches.map(e => {
          const parts = [e.course];
          if (e.faculty) parts.push(e.faculty);
          if (e.room)    parts.push(e.room);
          if (e.type === 'lab' && e.time_label) {
            parts.push(formatSlotToTime(e.time_label));
          }
          return parts.join(' | ');
        });
        row.push(cellParts.join(' ; '));
      }
    });
    rows.push(row);
  });

  return rows;
}

// ── BUILD ALL SECTIONS (for multi-sheet export) ───────────────────────────────
function buildTimetableSections(data) {
  const rawBatches = data.all_batches || batchList || [];
  // Exclude 'Whole Division' so it is not duplicated in sections
  const batches = rawBatches.filter(b => String(b).trim().toLowerCase() !== 'whole division');
  const sections = [];

  // Section 1: Whole Division (Theory only)
  sections.push({
    title: 'Whole Division',
    rows: buildGridForFilter(data, e => e.type === 'theory'),
  });

  // Section 2+: Each Batch (theory + that batch's labs)
  batches.forEach(batch => {
    sections.push({
      title: batch,
      rows: buildGridForFilter(data, e => {
        if (e.type === 'theory') return true;
        return (e.batch || '').toLowerCase() === batch.toLowerCase();
      }),
    });
  });

  return sections;
}

// ── BUILD FLAT ROWS (for CSV) ─────────────────────────────────────────────────
function buildTimetableGridRows(data) {
  const sections = buildTimetableSections(data);
  const days = data.days || [];
  const totalCols = days.length + 1; // 1 column for Time + number of days
  const allRows = [];

  sections.forEach((sec, sIdx) => {
    // Leave 3 blank rows between sections (starting from the 2nd section)
    if (sIdx > 0) {
      allRows.push(new Array(totalCols).fill(''));
      allRows.push(new Array(totalCols).fill(''));
      allRows.push(new Array(totalCols).fill(''));
    }

    // Center the batch title across the table columns
    const titleRow = new Array(totalCols).fill('');
    const midCol = Math.floor(totalCols / 2);
    titleRow[midCol] = `=== ${sec.title.toUpperCase()} ===`;
    allRows.push(titleRow);

    // Section table rows (headers + slot rows)
    sec.rows.forEach(r => allRows.push(r));
  });

  return allRows;
}

// ── CSV EXPORT ────────────────────────────────────────────────────────────────
// Uses UTF-8 BOM (\uFEFF) so Excel opens the file without garbled special chars.
// Quotes Time column so Excel reads time slots as text, never as date months.
document.getElementById('btn-export')?.addEventListener('click', () => {
  if (!lastResult) return;
  const rows = buildTimetableGridRows(lastResult);
  const csv = rows.map(r =>
    r.map(c => `"${String(c || '').replace(/"/g, '""')}"`).join(',')
  ).join('\r\n');

  const BOM = '\uFEFF';
  const blob = new Blob([BOM + csv], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'timetable.csv';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    if (a.parentNode) document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  }, 200);
});

// ── HELPER: LOAD SHEETJS DYNAMICALLY IF NEEDED ────────────────────────────────
function ensureSheetJS(callback) {
  if (typeof XLSX !== 'undefined') {
    callback(null, window.XLSX);
    return;
  }
  const s1 = document.createElement('script');
  s1.src = 'https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js';
  s1.onload = () => callback(null, window.XLSX);
  s1.onerror = () => {
    const s2 = document.createElement('script');
    s2.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
    s2.onload = () => callback(null, window.XLSX);
    s2.onerror = () => callback(new Error('Failed to load SheetJS library.'));
    document.head.appendChild(s2);
  };
  document.head.appendChild(s1);
}

// ── EXCEL EXPORT ──────────────────────────────────────────────────────────────
document.getElementById('btn-export-excel')?.addEventListener('click', () => {
  if (!lastResult) {
    alert('Please generate a timetable first.');
    return;
  }
  const btn = document.getElementById('btn-export-excel');
  const originalHtml = btn ? btn.innerHTML : 'Excel';
  if (btn) btn.textContent = 'Exporting…';

  ensureSheetJS((err, xlsxLib) => {
    if (btn) btn.innerHTML = originalHtml;
    if (err || !xlsxLib) {
      alert('Could not load Excel export library. Please check your internet connection.');
      return;
    }

    try {
      const sections = buildTimetableSections(lastResult);
      const wb = xlsxLib.utils.book_new();
      const usedSheetNames = new Set();

      sections.forEach(sec => {
        const ws = xlsxLib.utils.aoa_to_sheet(sec.rows);
        const colWidths = [];
        sec.rows.forEach(row => {
          row.forEach((cell, ci) => {
            const len = String(cell || '').length;
            if (!colWidths[ci] || colWidths[ci] < len) colWidths[ci] = len;
          });
        });
        ws['!cols'] = colWidths.map(w => ({ wch: Math.min(Math.max(w + 3, 10), 45) }));

        // Ensure safe & unique sheet name (max 31 chars, no invalid chars)
        let safeName = String(sec.title).replace(/[:\\\/\?\*\[\]]/g, '').trim().slice(0, 31) || 'Sheet';
        let uniqueName = safeName;
        let counter = 2;
        while (usedSheetNames.has(uniqueName.toLowerCase())) {
          uniqueName = safeName.slice(0, 27) + ' (' + counter + ')';
          counter++;
        }
        usedSheetNames.add(uniqueName.toLowerCase());

        xlsxLib.utils.book_append_sheet(wb, ws, uniqueName);
      });

      xlsxLib.writeFile(wb, 'timetable.xlsx');
    } catch (e) {
      alert('Failed to generate Excel file: ' + e.message);
    }
  });
});

// ── NLP HELPERS & TIMETABLE EDIT (CSV) ───────────────────────────────────────
window.addNlpConstraint = function(text) {
  const input = document.getElementById('nlp-constraints-input');
  if (!input) return;
  const current = input.value.trim();
  if (current) {
    input.value = current + '.\n' + text;
  } else {
    input.value = text;
  }
  input.focus();
  if (window.showToast) showToast('NLP constraint added!', 'info');
};

window.applySampleEdit = function(text) {
  const input = document.getElementById('input-edit-instruction');
  if (!input) return;
  input.value = text;
  input.focus();
};

let uploadedCsvContent = "";

const dropZone = document.getElementById('drop-zone-csv');
const fileInput = document.getElementById('input-edit-csv-file');
const statusPill = document.getElementById('csv-file-status');
const labelEl = document.getElementById('csv-upload-label');

dropZone?.addEventListener('click', () => fileInput.click());
dropZone?.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone?.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
    handleCsvFile(e.dataTransfer.files[0]);
  }
});

fileInput?.addEventListener('change', (e) => {
  if (e.target.files && e.target.files[0]) {
    handleCsvFile(e.target.files[0]);
  }
});

function handleCsvFile(file) {
  if (!file.name.toLowerCase().endsWith('.csv')) {
    alert('Please select a valid .csv file.');
    return;
  }
  const reader = new FileReader();
  reader.onload = function(evt) {
    uploadedCsvContent = evt.target.result;
    if (statusPill) {
      statusPill.style.display = 'inline-flex';
      const rowsCount = uploadedCsvContent.split('\n').filter(l => l.trim()).length;
      statusPill.innerHTML = `✓ <strong>${escHtml(file.name)}</strong> loaded (${rowsCount} rows ready for NLP)`;
    }
    if (labelEl) labelEl.textContent = 'Change file (' + file.name + ')';
    if (window.showToast) showToast('CSV timetable loaded successfully!', 'success');
  };
  reader.readAsText(file);
}

// Open Edit Modal buttons
document.getElementById('btn-open-edit')?.addEventListener('click', () => openModal('edit-timetable'));
document.getElementById('hero-btn-edit')?.addEventListener('click', () => openModal('edit-timetable'));

document.getElementById('btn-edit-active-tt')?.addEventListener('click', () => {
  if (lastResult) {
    const rows = buildTimetableGridRows(lastResult);
    uploadedCsvContent = rows.map(r =>
      r.map(c => `"${String(c || '').replace(/"/g, '""')}"`).join(',')
    ).join('\r\n');
    if (statusPill) {
      statusPill.style.display = 'inline-flex';
      statusPill.innerHTML = `✓ <strong>Current Active Timetable Loaded</strong> (ready to edit)`;
    }
    if (labelEl) labelEl.textContent = 'Using Active Timetable (click to change)';
  }
  openModal('edit-timetable');
});

// Submit Edit
const btnSubmitEdit = document.getElementById('btn-submit-edit');
btnSubmitEdit?.addEventListener('click', async () => {
  if (!uploadedCsvContent) {
    alert('Please upload a timetable CSV file first.');
    return;
  }
  const instruction = document.getElementById('input-edit-instruction')?.value.trim();
  if (!instruction) {
    alert('Please enter your requested changes in plain English.');
    document.getElementById('input-edit-instruction')?.focus();
    return;
  }

  const originalText = btnSubmitEdit.textContent;
  btnSubmitEdit.disabled = true;
  btnSubmitEdit.textContent = 'Processing NLP & Re-Evolving…';

  try {
    const res = await fetch('/api/edit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        csv_content: uploadedCsvContent,
        edit_instruction: instruction
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
      throw new Error(err.error || `Server error ${res.status}`);
    }
    const data = await res.json();
    lastResult = data;
    closeModal('edit-timetable');
    displayResultsUI(data);
    if (data.conflict_detected) {
      if (window.showToast) showToast('Conflict detected! Timetable was preserved without changes. See suggestions below.', 'error');
    } else {
      if (window.showToast) showToast('Timetable updated with NLP successfully!', 'success');
    }
  } catch (e) {
    alert('Error updating timetable: ' + e.message);
  } finally {
    btnSubmitEdit.disabled = false;
    btnSubmitEdit.textContent = originalText;
  }
});

// ── INIT ──────────────────────────────────────────────────────────────────────
(function init() {
  renderTheoryCourses();
  renderLabCourses();
  renderTheoryRooms();
  renderLabRooms();
  // Sync lunch dropdowns on first render
  if (window._syncLunchDropdowns) window._syncLunchDropdowns();
})();
