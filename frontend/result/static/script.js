// ==========================================================================
// MARKS ANALYSER — DESKTOP APPLICATION CONTROLLER
// Handles Tab Navigation, Window Controls, Data Grid Filtering,
// Chart Visualizations, and Student Modal Inspector.
// ==========================================================================

// Global Tab Switcher
function switchTab(tabId) {
  // Update nav tabs
  document.querySelectorAll('.nav-tab').forEach(tab => {
    if (tab.dataset.tab === tabId) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  // Update panes
  document.querySelectorAll('.desktop-pane').forEach(pane => {
    if (pane.id === `pane-${tabId}`) {
      pane.classList.add('active');
    } else {
      pane.classList.remove('active');
    }
  });

  // Update topbar title
  const titles = {
    'dashboard': 'Overview & Dashboard',
    'students': 'Student Register & Mark Cards',
    'subjects': 'Subject Performance Analytics',
    'failures': 'Remedial Register & Backlogs',
    'toppers': 'Toppers & Merit Rankings',
    'cohort': 'Year-Type Analysis',
    'export': 'Reports & Export Workspace'
  };
  const titleEl = document.getElementById('currentViewTitle');
  if (titleEl && titles[tabId]) {
    titleEl.textContent = titles[tabId];
  }
}

// Window Chrome Control Simulation
function initWindowControls() {
  const minBtn = document.getElementById('winMinBtn');
  const maxBtn = document.getElementById('winMaxBtn');
  const closeBtn = document.getElementById('winCloseBtn');

  if (minBtn) {
    minBtn.onclick = () => {
      document.body.classList.toggle('window-minimized');
      if (document.body.classList.contains('window-minimized')) {
        document.body.style.opacity = '0.4';
        setTimeout(() => { document.body.style.opacity = '1'; }, 700);
      }
    };
  }

  if (maxBtn) {
    maxBtn.onclick = () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
        maxBtn.textContent = '❐';
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen().catch(() => {});
        }
        maxBtn.textContent = '□';
      }
    };
  }

  if (closeBtn) {
    closeBtn.onclick = async () => {
      if (confirm('Close current ledger analysis in Marks Analyser?')) {
        try {
          await fetch('/reset', { method: 'POST' });
        } catch (e) {}
        window.location.reload();
      }
    };
  }
}

// Initialize Application Logic
document.addEventListener('DOMContentLoaded', () => {
  initWindowControls();

  // Tab click listeners
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      switchTab(tab.dataset.tab);
    });
  });

  // Upload Another PDF button in sidebar
  const uploadAnotherBtn = document.getElementById('uploadAnother');
  if (uploadAnotherBtn) {
    uploadAnotherBtn.onclick = async () => {
      if (confirm('Switch to another PDF? The current ledger will be reset.')) {
        try {
          await fetch('/reset', { method: 'POST' });
        } catch (e) {}
        window.location.reload();
      }
    };
  }

  // Parse server data
  const data = window.RESULT_DATA || {};
  const students = data.students || [];
  const subjectFailures = data.subject_failures || {};
  const subjectsList = data.subjects || [];

  // ================= 1. STUDENT REGISTER DATA GRID =================
  let currentPage = 1;
  const pageSize = 12;

  function getFilteredStudents() {
    const search = (document.getElementById('studentSearch')?.value || '').toLowerCase().trim();
    const resultFilter = document.getElementById('resultFilter')?.value || 'ALL';
    const yearFilter = document.getElementById('yearFilter')?.value || 'ALL';
    const sortVal = document.getElementById('sortSelect')?.value || 'total';

    let rows = students.filter(s => {
      const matchSearch = !search ||
        (s.name && s.name.toLowerCase().includes(search)) ||
        (s.usn && s.usn.toLowerCase().includes(search));
      const matchResult = (resultFilter === 'ALL') || (s.result === resultFilter);
      const matchYear = (yearFilter === 'ALL') || (s.year_type === yearFilter);
      return matchSearch && matchResult && matchYear;
    });

    rows.sort((a, b) => {
      if (sortVal === 'name') return (a.name || '').localeCompare(b.name || '');
      if (sortVal === 'percentage') return (b.percentage || 0) - (a.percentage || 0);
      return (b.total || 0) - (a.total || 0);
    });

    return rows;
  }

  function renderStudentTable() {
    const tableBody = document.querySelector('#studentTable tbody');
    if (!tableBody) return;

    const rows = getFilteredStudents();
    const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
    if (currentPage > totalPages) currentPage = totalPages;

    const startIdx = (currentPage - 1) * pageSize;
    const pagedRows = rows.slice(startIdx, startIdx + pageSize);

    if (pagedRows.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="7" class="empty-cell">No matching student records found.</td></tr>';
    } else {
      tableBody.innerHTML = pagedRows.map((s, idx) => {
        const globalRank = startIdx + idx + 1;
        const resBadge = s.result === 'PASS' ? 'badge pass' : 'badge fail';
        return `
          <tr data-usn="${s.usn}" title="Click to view detailed mark card">
            <td><b>#${globalRank}</b></td>
            <td><code style="font-family: var(--app-font-mono); color: #0f172a; font-weight:600;">${s.usn}</code></td>
            <td><strong>${s.name}</strong></td>
            <td><b>${s.total ?? '-'}</b> <span style="color:#94a3b8; font-size:11px;">/ 700</span></td>
            <td><b>${s.percentage != null ? s.percentage + '%' : '-'}</b></td>
            <td><span class="${resBadge}">${s.result}</span></td>
            <td><span style="color:#64748b; font-size:12px;">${s.year_type}</span></td>
          </tr>
        `;
      }).join('');
    }

    const pageLabel = document.getElementById('pageLabel');
    if (pageLabel) {
      pageLabel.textContent = `Page ${currentPage} of ${totalPages} (${rows.length} students)`;
    }

    // Attach click listeners to rows to open Inspector Dialog
    tableBody.querySelectorAll('tr[data-usn]').forEach(tr => {
      tr.addEventListener('click', () => {
        openStudentInspector(tr.dataset.usn);
      });
    });
  }

  // Pagination Listeners
  const prevBtn = document.getElementById('prevPage');
  const nextBtn = document.getElementById('nextPage');

  if (prevBtn) {
    prevBtn.onclick = () => {
      if (currentPage > 1) {
        currentPage--;
        renderStudentTable();
      }
    };
  }

  if (nextBtn) {
    nextBtn.onclick = () => {
      const rows = getFilteredStudents();
      const totalPages = Math.ceil(rows.length / pageSize);
      if (currentPage < totalPages) {
        currentPage++;
        renderStudentTable();
      }
    };
  }

  // Filter Listeners
  ['studentSearch', 'resultFilter', 'yearFilter', 'sortSelect'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => {
        currentPage = 1;
        renderStudentTable();
      });
    }
  });

  // ================= 2. STUDENT INSPECTOR MODAL =================
  function openStudentInspector(usn) {
    const student = students.find(s => s.usn === usn);
    if (!student) return;

    const modal = document.getElementById('studentModal');
    const modalContent = document.getElementById('modalContent');
    if (!modal || !modalContent) return;

    const subjectRows = Object.entries(student.subjects || {}).map(([code, sub]) => {
      const meta = subjectsList.find(x => x.code === code) || { name: code };
      const statusBadge = sub.status === 'PASS' ? 'badge pass' : 'badge fail';
      return `
        <tr>
          <td>
            <strong>${meta.name}</strong>
            <small style="display:block; color:#64748b; font-family:var(--app-font-mono); font-size:10px;">${code}</small>
          </td>
          <td>${sub.theory ?? '-'}</td>
          <td>${sub.internal ?? '-'}</td>
          <td><b>${sub.total ?? '-'}</b></td>
          <td><span class="${statusBadge}">${sub.status}</span></td>
        </tr>
      `;
    }).join('');

    modalContent.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--panel-border);">
        <div>
          <span style="font-size: 10px; font-weight: 800; color: var(--accent-red); letter-spacing: 0.8px;">OFFICIAL RESULT LEDGER</span>
          <h2 style="font-size: 22px; margin: 4px 0 2px;">${student.name}</h2>
          <div style="font-family: var(--app-font-mono); color: #64748b; font-size: 13px;">
            ${student.usn} · <span style="color:#0f172a; font-weight:600;">${student.year_type}</span>
          </div>
        </div>
        <div style="text-align: right;">
          <span class="badge ${student.result === 'PASS' ? 'pass' : 'fail'}" style="font-size: 13px; padding: 6px 14px;">${student.result}</span>
        </div>
      </div>

      <div class="desktop-table-container" style="max-height: 280px; margin-bottom: 20px;">
        <table class="desktop-table">
          <thead>
            <tr>
              <th>Subject</th>
              <th>Theory</th>
              <th>Internal</th>
              <th>Total</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${subjectRows || '<tr><td colspan="5" class="empty-cell">No subject marks available.</td></tr>'}
          </tbody>
        </table>
      </div>

      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px;">
        <div style="background: #f8fafc; padding: 12px; border-radius: var(--radius-md); border: 1px solid var(--panel-border);">
          <small style="color: #64748b; font-size: 11px;">Grand Total</small>
          <div style="font-size: 20px; font-weight: 700; font-family: var(--app-font-brand); color: #0f172a;">${student.total ?? '-'} <span style="font-size: 12px; color: #94a3b8;">/ 700</span></div>
        </div>
        <div style="background: #f8fafc; padding: 12px; border-radius: var(--radius-md); border: 1px solid var(--panel-border);">
          <small style="color: #64748b; font-size: 11px;">Percentage</small>
          <div style="font-size: 20px; font-weight: 700; font-family: var(--app-font-brand); color: #0f172a;">${student.percentage != null ? student.percentage + '%' : '-'}</div>
        </div>
        <div style="background: #f8fafc; padding: 12px; border-radius: var(--radius-md); border: 1px solid var(--panel-border);">
          <small style="color: #64748b; font-size: 11px;">Semester Outcome</small>
          <div style="font-size: 20px; font-weight: 700; font-family: var(--app-font-brand); color: ${student.result === 'PASS' ? '#15803d' : '#b91c1c'};">${student.result}</div>
        </div>
      </div>

      <div style="padding: 10px 14px; background: #f1f5f9; border-radius: var(--radius-md); font-size: 12px; color: #475569; display: flex; justify-content: space-between;">
        <span>SGPA: <b>${student.sgpa || '-'}</b></span>
        <span>CGPA: <b>${student.cgpa || '-'}</b></span>
        <span>Class: <b>${student.grade || 'Not exposed'}</b></span>
      </div>
    `;

    modal.classList.add('open');
  }

  const closeModalBtn = document.getElementById('closeModal');
  const modalEl = document.getElementById('studentModal');
  if (closeModalBtn) {
    closeModalBtn.onclick = () => modalEl.classList.remove('open');
  }
  if (modalEl) {
    modalEl.onclick = (e) => {
      if (e.target === modalEl) modalEl.classList.remove('open');
    };
  }

  // ================= 3. FAILURE VIEW =================
  const subjectSelect = document.getElementById('subjectSelect');
  function renderSubjectFailures() {
    if (!subjectSelect) return;
    const selectedCode = subjectSelect.value;
    const failedList = subjectFailures[selectedCode] || [];

    const failureCountEl = document.getElementById('failureCount');
    if (failureCountEl) {
      failureCountEl.textContent = `${failedList.length} student${failedList.length === 1 ? '' : 's'} failed this subject`;
    }

    const tableBody = document.getElementById('failureTable');
    if (!tableBody) return;

    if (failedList.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="6" class="empty-cell">No failed students for this subject.</td></tr>';
    } else {
      tableBody.innerHTML = failedList.map(s => `
        <tr>
          <td><code style="font-family: var(--app-font-mono); font-weight: 600;">${s.usn}</code></td>
          <td><strong>${s.name}</strong></td>
          <td>${s.theory ?? '-'}</td>
          <td>${s.internal ?? '-'}</td>
          <td><b>${s.total ?? '-'}</b></td>
          <td><span class="badge fail">${s.status || 'FAIL'}</span></td>
        </tr>
      `).join('');
    }
  }

  if (subjectSelect) {
    subjectSelect.addEventListener('change', renderSubjectFailures);
  }

  // ================= 4. CHART.JS VISUALIZATIONS =================
  if (subjectsList.length > 0 && typeof Chart !== 'undefined') {
    const labels = subjectsList.map(s => {
      return s.name.length > 20 ? s.name.substring(0, 18) + '...' : s.name;
    });

    const passPercentages = subjectsList.map(s => s.pass_percentage);
    const averages = subjectsList.map(s => s.average);
    const failureCounts = subjectsList.map(s => s.failed);

    const defaultOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: '#f1f5f9' },
          ticks: { font: { family: 'Inter', size: 11 }, color: '#64748b' }
        },
        x: {
          grid: { display: false },
          ticks: { font: { family: 'Inter', size: 10 }, color: '#64748b', maxRotation: 25 }
        }
      }
    };

    // Pass Chart
    const passCanvas = document.getElementById('passChart');
    if (passCanvas) {
      new Chart(passCanvas, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            data: passPercentages,
            backgroundColor: '#3b82f6',
            borderRadius: 6
          }]
        },
        options: defaultOptions
      });
    }

    // Average Chart
    const avgCanvas = document.getElementById('averageChart');
    if (avgCanvas) {
      new Chart(avgCanvas, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            data: averages,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.35,
            borderWidth: 2.5,
            pointRadius: 4,
            pointBackgroundColor: '#10b981'
          }]
        },
        options: defaultOptions
      });
    }

    // Fail Chart
    const failCanvas = document.getElementById('failChart');
    if (failCanvas) {
      new Chart(failCanvas, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [{
            data: failureCounts,
            backgroundColor: '#ea2839',
            borderRadius: 6
          }]
        },
        options: defaultOptions
      });
    }
  }

  // Initial table & failure render
  renderStudentTable();
  renderSubjectFailures();
});
