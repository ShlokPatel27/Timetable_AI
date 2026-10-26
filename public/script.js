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

let timeSlots = ['8-9','9-10','10-11','11-12','12-1','1-2','2-3','3-4'];
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
  document.querySelector('.btn-primary__text').hidden = true;
  document.querySelector('.btn-primary__loader').hidden = false;

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
    renderResults(data);
  } catch (e) {
    alert('Error: ' + e.message);
  } finally {
    btnRun.disabled = false;
    document.querySelector('.btn-primary__text').hidden = false;
    document.querySelector('.btn-primary__loader').hidden = true;
  }
});

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

  // Show results FIRST so canvas has real dimensions, then draw chart
  document.getElementById('results').hidden = false;
  requestAnimationFrame(() => renderChart(data.fitness_history));
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

// ── BUILD TIMETABLE GRID (single section) ─────────────────────────────────────
function buildGridForFilter(data, filterFn) {
  const schedule = data.schedule || [];
  const days = data.days || [];
  const slots = data.time_slots || [];
  const rows = [];

  // Header row: Time | Mon | Tue | Wed | ...
  rows.push(['Time', ...days]);

  slots.forEach(slot => {
    const row = [slot];
    days.forEach(day => {
      const matches = schedule.filter(e =>
        filterFn(e) && e.day === day && (e.time_label||'').startsWith(slot)
      );
      if (matches.length === 0) {
        row.push('—');
      } else {
        const cellParts = matches.map(e => {
          const parts = [e.course];
          if (e.faculty) parts.push(e.faculty);
          if (e.room)    parts.push(e.room);
          if (e.type === 'lab' && e.time_label) parts.push(e.time_label);
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
  const batches = data.all_batches || batchList || [];
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
  const allRows = [];

  sections.forEach(sec => {
    allRows.push([`═══ ${sec.title.toUpperCase()} ═══`, ...days.map(() => '')]);
    sec.rows.forEach(r => allRows.push(r));
    allRows.push(days.map(() => '').concat(''));
  });

  return allRows;
}

// ── CSV EXPORT ────────────────────────────────────────────────────────────────
document.getElementById('btn-export')?.addEventListener('click', () => {
  if (!lastResult) return;
  const rows = buildTimetableGridRows(lastResult);
  const csv = rows.map(r =>
    r.map(c => `"${String(c||'').replace(/"/g,'""')}"`).join(',')
  ).join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download = 'timetable.csv'; a.click();
});

// ── SHEETS EXPORT (Multi-Tab) ─────────────────────────────────────────────────
document.getElementById('btn-share')?.addEventListener('click', async () => {
  if (!lastResult) { alert('Generate a timetable first.'); return; }
  const ssId  = (document.getElementById('input-spreadsheet-id')?.value||'').trim();
  const fldId = (document.getElementById('input-folder-id')?.value||'').trim();
  if (!ssId) return;

  const btn     = document.getElementById('btn-share');
  const textEl  = btn.querySelector('.btn-primary__text');
  const loadEl  = btn.querySelector('.btn-primary__loader');
  textEl.hidden = true; loadEl.hidden = false; btn.disabled = true;

  const sections = buildTimetableSections(lastResult);
  try {
    const res = await fetch('/api/export_google_sheets', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ sections, spreadsheet_id:ssId, folder_id:fldId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error||`HTTP ${res.status}`);
    alert('Exported! Opening your sheet…');
    window.open(data.url, '_blank');
  } catch(e) {
    alert('Export failed: '+e.message);
  } finally {
    textEl.hidden = false; loadEl.hidden = true; btn.disabled = false;
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
