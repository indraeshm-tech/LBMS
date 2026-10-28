/**
 * main.js - Interactive LBMS GUI Controller
 * Developed by Fathima Afroz, iPEC Solutions, Bangalore
 * Theme: Electric Kiwi
 */

document.addEventListener('DOMContentLoaded', function () {
  initBookDropdown();
  initTabs();
  initFineCalculator();
  initReturnSelector();
  initTableSearch();
  initModalControls();
});

// 1. Available Book Dropdown Controller
function initBookDropdown() {
  const bookSelect = document.getElementById('available-book-select');
  const previewBadge = document.getElementById('book-preview-badge');

  if (!bookSelect) return;

  bookSelect.addEventListener('change', function () {
    const isbn = this.value;
    if (!isbn) {
      if (previewBadge) previewBadge.classList.remove('active');
      return;
    }

    fetch(`/api/book/${encodeURIComponent(isbn)}`)
      .then(res => res.json())
      .then(data => {
        if (data.success && data.book) {
          const b = data.book;
          if (previewBadge) {
            document.getElementById('prev-title').textContent = b.Title;
            document.getElementById('prev-author').textContent = `By: ${b.Author}`;
            document.getElementById('prev-isbn').textContent = `ISBN: ${b.ISBN}`;
            document.getElementById('prev-price').textContent = `Price: ₹${parseFloat(b.Price).toFixed(2)}`;
            document.getElementById('prev-copies').textContent = `Available: ${b.AvailableCopies} Copies`;
            previewBadge.classList.add('active');
          }

          // Auto-fill Issue Form inputs if present
          const issueIsbn = document.getElementById('issue_isbn');
          const issueTitle = document.getElementById('issue_title');
          const issueAuthor = document.getElementById('issue_author');

          if (issueIsbn) issueIsbn.value = b.ISBN;
          if (issueTitle) issueTitle.value = b.Title;
          if (issueAuthor) issueAuthor.value = b.Author;

          // Auto-fill Fine Simulator Price
          const simPrice = document.getElementById('sim_price');
          if (simPrice) {
            simPrice.value = b.Price;
            triggerFineCalculation();
          }
        }
      })
      .catch(err => console.error("Error fetching book details:", err));
  });
}

// 2. Tab Navigation
function initTabs() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', function () {
      const targetTab = this.getAttribute('data-tab');
      const parentCard = this.closest('.lbms-card');

      // Update button active state
      parentCard.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      this.classList.add('active');

      // Update pane active state
      parentCard.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      const activePane = parentCard.querySelector(`#${targetTab}`);
      if (activePane) activePane.classList.add('active');
    });
  });
}

// 3. Dynamic Fine & Penalty Calculator
function initFineCalculator() {
  const dueDateInput = document.getElementById('sim_due_date');
  const returnDateInput = document.getElementById('sim_return_date');
  const priceInput = document.getElementById('sim_price');
  const lostCheckbox = document.getElementById('sim_is_lost');

  if (!dueDateInput || !returnDateInput) return;

  [dueDateInput, returnDateInput, priceInput, lostCheckbox].forEach(el => {
    if (el) {
      el.addEventListener('input', triggerFineCalculation);
      el.addEventListener('change', triggerFineCalculation);
    }
  });
}

function triggerFineCalculation() {
  const dueDate = document.getElementById('sim_due_date')?.value;
  const returnDate = document.getElementById('sim_return_date')?.value;
  const price = parseFloat(document.getElementById('sim_price')?.value || 0);
  const isLost = document.getElementById('sim_is_lost')?.checked || false;

  const resultContainer = document.getElementById('calc-results');
  const totalDisplay = document.getElementById('calc-total-val');
  const breakdownList = document.getElementById('calc-breakdown-list');

  if (!dueDate || !returnDate) {
    if (resultContainer) resultContainer.style.display = 'none';
    return;
  }

  fetch('/api/calculate_fine', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      due_date: dueDate,
      return_date: returnDate,
      price: price,
      is_lost: isLost
    })
  })
    .then(res => res.json())
    .then(data => {
      if (resultContainer) resultContainer.style.display = 'block';
      if (totalDisplay) totalDisplay.textContent = `₹${parseFloat(data.total_payable).toFixed(2)}`;

      if (breakdownList) {
        breakdownList.innerHTML = '';
        data.breakdown.forEach(item => {
          const div = document.createElement('div');
          div.className = 'calc-breakdown-item';
          div.textContent = `• ${item}`;
          breakdownList.appendChild(div);
        });
      }
    })
    .catch(err => console.error("Error calculating fine:", err));
}

// 4. Return Selector Auto-fill
function initReturnSelector() {
  const returnSelect = document.getElementById('return_issue_id');
  const returnDateInput = document.getElementById('return_date_input');
  const returnLostCheck = document.getElementById('return_is_lost');
  const previewDiv = document.getElementById('return-preview-info');

  if (!returnSelect) return;

  function updateReturnPreview() {
    const selectedOption = returnSelect.options[returnSelect.selectedIndex];
    if (!selectedOption || !selectedOption.value) {
      if (previewDiv) previewDiv.style.display = 'none';
      return;
    }

    const dueDate = selectedOption.getAttribute('data-duedate');
    const price = parseFloat(selectedOption.getAttribute('data-price') || 0);
    const returnDate = returnDateInput?.value || new Date().toISOString().split('T')[0];
    const isLost = returnLostCheck?.checked || false;

    fetch('/api/calculate_fine', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        due_date: dueDate,
        return_date: returnDate,
        price: price,
        is_lost: isLost
      })
    })
      .then(res => res.json())
      .then(data => {
        if (previewDiv) {
          previewDiv.style.display = 'block';
          const fineTag = document.getElementById('ret-fine-est');
          const statusTag = document.getElementById('ret-status-est');

          if (data.days_overdue > 0) {
            fineTag.textContent = `Overdue: ${data.days_overdue} days | Payable: ₹${data.total_payable.toFixed(2)}`;
            fineTag.className = 'badge badge-danger';
          } else {
            fineTag.textContent = isLost ? `Payable Penalty: ₹${data.total_payable.toFixed(2)}` : 'On Time | Zero Fine';
            fineTag.className = isLost ? 'badge badge-warning' : 'badge badge-success';
          }

          if (isLost) {
            statusTag.textContent = 'Book marked as LOST (Price + Overdue)';
          } else {
            statusTag.textContent = 'Safe Return';
          }
        }
      });
  }

  returnSelect.addEventListener('change', updateReturnPreview);
  if (returnDateInput) returnDateInput.addEventListener('change', updateReturnPreview);
  if (returnLostCheck) returnLostCheck.addEventListener('change', updateReturnPreview);
}

// 5. Table Real-time Search
function initTableSearch() {
  const searchInput = document.getElementById('book-search-input');
  const bookTable = document.getElementById('books-table');

  if (!searchInput || !bookTable) return;

  searchInput.addEventListener('input', function () {
    const query = this.value.toLowerCase().trim();
    const rows = bookTable.querySelectorAll('tbody tr');

    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      if (text.includes(query)) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  });
}

// 6. Modal Controls
function initModalControls() {
  const openButtons = document.querySelectorAll('[data-modal-target]');
  const closeButtons = document.querySelectorAll('.modal-close-btn');
  const overlays = document.querySelectorAll('.modal-overlay');

  openButtons.forEach(btn => {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      const targetId = this.getAttribute('data-modal-target');
      const targetModal = document.getElementById(targetId);
      if (targetModal) targetModal.classList.add('active');
    });
  });

  closeButtons.forEach(btn => {
    btn.addEventListener('click', function () {
      this.closest('.modal-overlay').classList.remove('active');
    });
  });

  overlays.forEach(overlay => {
    overlay.addEventListener('click', function (e) {
      if (e.target === this) {
        this.classList.remove('active');
      }
    });
  });
}

// Helper: Print page
function printDocument() {
  window.print();
}
