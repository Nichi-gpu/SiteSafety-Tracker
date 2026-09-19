/**
 * SiteSafety Tracker - Core Application Logic
 * Shared across Staff and Administrator portals.
 */

document.addEventListener('DOMContentLoaded', () => {
  /* ============================================
     1. TOAST NOTIFICATION UTILITY
     ============================================ */
  function showToast(message, type = 'info', duration = 3600) {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconSvg = '';
    if (type === 'success') {
      iconSvg = `
        <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>`;
    } else if (type === 'error') {
      iconSvg = `
        <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>`;
    } else {
      iconSvg = `
        <svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>`;
    }

    toast.innerHTML = `${iconSvg}<span>${escapeHTML(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('toast-hiding');
      setTimeout(() => {
        toast.remove();
      }, 300);
    }, duration);
  }
  window.showToast = showToast;

  /* ============================================
     USER SESSION & PROFILE DROPDOWN
     ============================================ */
  function initUserSession() {
    const rawUsername = localStorage.getItem('username');
    const email = localStorage.getItem('userEmail') || '';
    const username = rawUsername || (email ? email.split('@')[0] : 'User');
    const role = (localStorage.getItem('userRole') || 'staff').toLowerCase();

    // Top-right dropdown display
    const nameEls = document.querySelectorAll('#display-account-name, .user-name');
    nameEls.forEach(el => {
      if (el) el.textContent = username;
    });

    // Sidebar footer display (Option A: displays username and role)
    const sidebarUsernames = document.querySelectorAll('#sidebar-username-label');
    sidebarUsernames.forEach(el => {
      if (el) el.textContent = username;
    });

    const sidebarRoles = document.querySelectorAll('#sidebar-role-label');
    const roleTitle = (role === 'manager' || role === 'admin') ? 'Administrator' : 'Reporting Personnel';
    sidebarRoles.forEach(el => {
      if (el) el.textContent = roleTitle;
    });
  }
  initUserSession();

  /* ============================================
     2. UNIFIED DATA STORAGE & SEEDING
     ============================================ */

  // Initial Seed for Hazards (Only genuine user-created reports)
  function initHazardStore() {
    const raw = localStorage.getItem('SiteSafety_Hazards');
    let hazards = [];
    if (raw) {
      try {
        hazards = JSON.parse(raw);
        if (!Array.isArray(hazards)) hazards = [];
      } catch (e) {
        console.error('Error parsing SiteSafety_Hazards:', e);
        hazards = [];
      }
    }

    // Purge mock/sample seed hazards so only genuine user-created reports remain
    const mockReporters = ['Michael Vance', 'Elena Gomez', 'Dr. Robert Hayes', 'Dr. Hayes', 'Marcus Sterling', 'Sarah Lin', 'Jennifer Ward', 'David Kim', 'Angela Brooks'];
    hazards = hazards.filter(h => {
      if (!h || !h.ticket) return false;
      const isMockTicket = /^ABC-2026-(0315|0316|0310|0305)-/i.test(h.ticket);
      const isMockReporter = h.personnel && mockReporters.includes(h.personnel.name);
      return !isMockTicket && !isMockReporter;
    });

    localStorage.setItem('SiteSafety_Hazards', JSON.stringify(hazards));
    return hazards;
  }

  function getStoredHazards() {
    return initHazardStore();
  }

  function saveStoredHazards(hazards) {
    localStorage.setItem('SiteSafety_Hazards', JSON.stringify(hazards));
  }

  // Initial Seed for Scheduled Inspections
  function initInspectionStore() {
    const raw = localStorage.getItem('SiteSafety_Inspections');
    if (raw) {
      try {
        return JSON.parse(raw);
      } catch (e) {
        console.error('Error parsing SiteSafety_Inspections:', e);
      }
    }

    const defaultInspections = [
      // Page 1
      { title: 'Tower Crane Integrity Check', location: 'Site A - Sector 3', inspector: 'Marcus Vance', date: '09-18-26', time: '09:00 AM', status: 'Scheduled' },
      { title: 'Scaffolding Safety Audit', location: 'Site B - Main Gate', inspector: 'Elena Gomez', date: '09-18-26', time: '11:30 AM', status: 'Scheduled' },
      { title: 'Electrical Rig Wiring Review', location: 'Site C - Generator 2', inspector: 'David Kim', date: '09-19-26', time: '01:15 PM', status: 'Scheduled' },
      { title: 'Excavation Shoring Inspection', location: 'Site A - Trench 4', inspector: 'Carlos Mendez', date: '09-19-26', time: '03:45 PM', status: 'Scheduled' },
      { title: 'PPE Compliance Patrol', location: 'Site B - Warehouse 2', inspector: 'Sarah Lin', date: '09-20-26', time: '10:00 AM', status: 'Scheduled' },
      { title: 'Chemical Storage Assessment', location: 'Site C - Hazmat Bay', inspector: 'Dr. Hayes', date: '09-20-26', time: '02:00 PM', status: 'Scheduled' },
      // Page 2
      { title: 'Fire Suppression Pipeline Test', location: 'Site A - Sublevel 1', inspector: 'Angela Brooks', date: '09-21-26', time: '08:30 AM', status: 'Scheduled' },
      { title: 'Fall Arrest Anchor Audit', location: 'Site B - Roof Deck', inspector: 'Marcus Sterling', date: '09-21-26', time: '10:45 AM', status: 'Scheduled' },
      { title: 'Concrete Pour Formwork Check', location: 'Site C - Block D', inspector: 'Jennifer Ward', date: '09-22-26', time: '01:00 PM', status: 'Scheduled' },
      { title: 'Heavy Plant Machinery Inspection', location: 'Site A - Depot 1', inspector: 'Michael Vance', date: '09-22-26', time: '03:30 PM', status: 'Scheduled' },
      { title: 'First Aid Station Supply Audit', location: 'Site B - Clinic Area', inspector: 'Elena Gomez', date: '09-23-26', time: '09:15 AM', status: 'Scheduled' },
      { title: 'Perimeter Barrier Stability Review', location: 'Site C - Boundary North', inspector: 'David Kim', date: '09-23-26', time: '11:00 AM', status: 'Scheduled' },
      // Page 3
      { title: 'Emergency Egress Pathway Check', location: 'Site A - Sector 1', inspector: 'Sarah Lin', date: '09-24-26', time: '09:00 AM', status: 'Scheduled' },
      { title: 'Ventilation & Air Quality Review', location: 'Site B - Subterranean', inspector: 'Dr. Hayes', date: '09-24-26', time: '11:30 AM', status: 'Scheduled' },
      { title: 'Hydraulic Lift Systems Testing', location: 'Site C - Sector 2', inspector: 'Carlos Mendez', date: '09-25-26', time: '01:45 PM', status: 'Scheduled' },
      { title: 'Ground Resistance & Earthing Check', location: 'Site A - Transformer 1', inspector: 'David Kim', date: '09-25-26', time: '03:15 PM', status: 'Scheduled' },
      { title: 'Confined Space Entry Signoff', location: 'Site B - Tank 3', inspector: 'Marcus Sterling', date: '09-26-26', time: '10:00 AM', status: 'Scheduled' },
      { title: 'Hazardous Waste Manifest Audit', location: 'Site C - Disposal Area', inspector: 'Angela Brooks', date: '09-26-26', time: '02:30 PM', status: 'Scheduled' }
    ];

    localStorage.setItem('SiteSafety_Inspections', JSON.stringify(defaultInspections));
    return defaultInspections;
  }

  function getStoredInspections() {
    return initInspectionStore();
  }

  function saveStoredInspections(inspections) {
    localStorage.setItem('SiteSafety_Inspections', JSON.stringify(inspections));
  }

  // Initial Seed for System Notifications
  function initNotificationStore() {
    const raw = localStorage.getItem('SiteSafety_Notifications');
    let notifs = [];
    if (raw) {
      try {
        notifs = JSON.parse(raw);
        if (!Array.isArray(notifs)) notifs = [];
      } catch (e) {
        console.error('Error parsing SiteSafety_Notifications:', e);
        notifs = [];
      }
    }

    // Purge mock seed notifications (IDs 1, 2, 3 or placeholder protocol/scaffolding texts)
    notifs = notifs.filter(n => {
      if (!n || !n.title) return false;
      if (n.id === '1' || n.id === '2' || n.id === '3') return false;
      if (n.title.includes('New Safety Protocol Published for Q3')) return false;
      if (n.title.includes('Scaffolding Audit Inspection Completed')) return false;
      if (n.title.includes('ABC-2026-0310-01 Marked as Resolved')) return false;
      return true;
    });

    localStorage.setItem('SiteSafety_Notifications', JSON.stringify(notifs));
    return notifs;
  }

  function getStoredNotifications() {
    return initNotificationStore();
  }

  function saveStoredNotifications(notifs) {
    localStorage.setItem('SiteSafety_Notifications', JSON.stringify(notifs));
    updateNotifBadge();
  }

  function updateNotifBadge() {
    const notifs = getStoredNotifications();
    const hasUnread = notifs.some(n => n && n.unread);
    const badges = document.querySelectorAll('.notif-badge');
    badges.forEach(badge => {
      badge.style.display = hasUnread ? 'block' : 'none';
    });
  }
  // Initialize notification badge state on page load
  updateNotifBadge();

  function addNotification(title, meta = {}) {
    const notifs = getStoredNotifications();
    notifs.unshift({
      id: Date.now().toString(),
      title: title,
      time: 'Just now',
      unread: true,
      ...meta
    });
    saveStoredNotifications(notifs);
  }

  /* ============================================
     3. CSV EXPORT HELPER
     ============================================ */
  function exportToCSV(filename, rows, headers) {
    if (!rows || !rows.length) {
      showToast('No records available to export.', 'info');
      return;
    }
    const csvRows = [];
    csvRows.push(headers.map(h => `"${h.label.replace(/"/g, '""')}"`).join(','));

    for (const row of rows) {
      const values = headers.map(h => {
        let val = typeof h.key === 'function' ? h.key(row) : (row[h.key] ?? '');
        val = String(val).replace(/"/g, '""');
        return `"${val}"`;
      });
      csvRows.push(values.join(','));
    }

    const csvContent = 'data:text/csv;charset=utf-8,\uFEFF' + encodeURIComponent(csvRows.join('\r\n'));
    const link = document.createElement('a');
    link.setAttribute('href', csvContent);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    showToast(`Exported ${rows.length} records to ${filename}!`, 'success');
  }

  /* ============================================
     4. SESSION, USER ROLE & ROUTE GUARDING
     ============================================ */
  const userEmail = localStorage.getItem('userEmail');
  const selectedRole = localStorage.getItem('selectedRole') || 'staff';
  const displayAccountName = document.getElementById('display-account-name');
  const sidebarRoleLabel = document.getElementById('sidebar-role-label');
  const navDashboardSubtitle = document.getElementById('nav-dashboard-subtitle');

  // Display user's account name if logged in
  if (displayAccountName) {
    const emailToUse = userEmail || (selectedRole === 'manager' ? 'manager@sitesafety.com' : 'andrei@sitesafety.com');
    const username = emailToUse.split('@')[0];
    const formattedName = username.charAt(0).toUpperCase() + username.slice(1);
    displayAccountName.textContent = formattedName || 'Account Name';
  }

  // Update role badge/label
  if (selectedRole === 'manager') {
    if (sidebarRoleLabel) sidebarRoleLabel.textContent = 'Administrator';
    if (navDashboardSubtitle) navDashboardSubtitle.textContent = "ADMINISTRATOR'S DASHBOARD";
  } else {
    if (sidebarRoleLabel) sidebarRoleLabel.textContent = 'Reporting Personnel';
    if (navDashboardSubtitle) navDashboardSubtitle.textContent = "REPORTING PERSONNEL'S DASHBOARD";
  }

  /* ============================================
     5. NOTIFICATION BELL CENTER & ACTIVITY DRAWER
     ============================================ */
  const notifBtn = document.getElementById('notif-btn');
  if (notifBtn) {
    // Create notif-dropdown if not present
    let notifDropdown = document.getElementById('notif-dropdown');
    if (!notifDropdown) {
      notifDropdown = document.createElement('div');
      notifDropdown.id = 'notif-dropdown';
      notifDropdown.className = 'notif-dropdown';
      notifDropdown.setAttribute('role', 'dialog');
      notifDropdown.setAttribute('aria-label', 'Recent Notifications');

      notifDropdown.innerHTML = `
        <div class="notif-dropdown-header">
          <span>Notifications</span>
          <button type="button" class="clear-notifs-btn" id="btn-clear-notifs">Clear all</button>
        </div>
        <div class="notif-list" id="notif-list-container"></div>
      `;
      // Position relative to navbar nav-right
      const navRight = document.querySelector('.nav-right');
      if (navRight) {
        navRight.style.position = 'relative';
        navRight.appendChild(notifDropdown);
      }
    }

    function resolveNotificationTarget(notif) {
      const isManager = (localStorage.getItem('selectedRole') === 'manager');
      const title = (notif.title || '').toLowerCase();
      
      if (notif.url) {
        return notif.url;
      }

      // Check for ticket in notification (e.g. ABC-2026-0310-01)
      const ticketMatch = (notif.title || '').match(/[A-Z0-9]+-\d{4}-\d{4}-\d+/i);
      const ticketId = ticketMatch ? ticketMatch[0] : (notif.ticket || null);

      // 1. Resolved hazard notification
      if (title.includes('resolved')) {
        return isManager ? 'manager-resolved.html' : 'report-history.html';
      }

      // 2. Pending / Filed hazard notification
      if (title.includes('hazard') || title.includes('incident') || title.includes('ticket')) {
        if (ticketId) {
          const allHazards = getStoredHazards();
          const found = allHazards.find(h => h.ticket.toLowerCase() === ticketId.toLowerCase());
          if (found) {
            localStorage.setItem('lastSubmittedReport', JSON.stringify(found));
          }
          return isManager ? `manager-home.html?ticket=${encodeURIComponent(ticketId)}` : 'report-status.html';
        }
        return isManager ? 'manager-home.html' : 'report-status.html';
      }

      // 3. Inspection notification
      if (title.includes('inspect') || title.includes('audit')) {
        return isManager ? 'manager-add-inspection.html' : 'dashboard.html';
      }

      // 4. Safety protocol / policy
      if (title.includes('protocol') || title.includes('policy') || title.includes('guide')) {
        return isManager ? 'manager-home.html' : 'dashboard.html';
      }

      // Default fallback
      return isManager ? 'manager-home.html' : 'home.html';
    }

    function renderNotifications() {
      const listContainer = document.getElementById('notif-list-container');
      if (!listContainer) return;
      const notifs = getStoredNotifications();

      if (!notifs || notifs.length === 0) {
        listContainer.innerHTML = `<div class="notif-empty">No notifications right now</div>`;
        return;
      }

      listContainer.innerHTML = notifs
        .map(
          n => `
        <div class="notif-item ${n.unread ? 'unread' : ''}" data-id="${escapeHTML(n.id)}" tabindex="0" role="button" title="Click to view">
          <div class="notif-item-top">
            <span class="notif-item-title">${escapeHTML(n.title)}</span>
            ${n.unread ? '<span class="notif-unread-dot" title="Unread"></span>' : ''}
          </div>
          <div class="notif-item-bottom">
            <span class="notif-item-time">${escapeHTML(n.time)}</span>
            <span class="notif-item-link-text">Go to page &rarr;</span>
          </div>
        </div>`
        )
        .join('');

      // Wire click and keyboard navigation on each notification
      listContainer.querySelectorAll('.notif-item').forEach(item => {
        const notifId = item.getAttribute('data-id');
        const notif = notifs.find(n => n.id === notifId);
        if (!notif) return;

        const handleNotifClick = () => {
          // Mark as read
          notif.unread = false;
          saveStoredNotifications(notifs);

          // Close dropdown
          notifDropdown.classList.remove('show');

          // Resolve target URL
          const targetUrl = resolveNotificationTarget(notif);
          
          // Check if already on manager-home.html with active detail function
          const ticketMatch = (notif.title || '').match(/[A-Z0-9]+-\d{4}-\d{4}-\d+/i);
          const ticketId = ticketMatch ? ticketMatch[0] : (notif.ticket || null);

          if (ticketId && window.location.pathname.includes('manager-home.html') && typeof openHazardDetail === 'function') {
            const allHazards = getStoredHazards();
            const found = allHazards.find(h => h.ticket.toLowerCase() === ticketId.toLowerCase());
            if (found) {
              openHazardDetail(found);
              return;
            }
          }

          // Navigate to destination
          window.location.href = targetUrl;
        };

        item.addEventListener('click', handleNotifClick);
        item.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleNotifClick();
          }
        });
      });
    }

    notifBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = notifDropdown.classList.contains('show');
      notifDropdown.classList.toggle('show', !isOpen);

      if (!isOpen) {
        // Mark all notifications as read when viewed
        const notifs = getStoredNotifications();
        let changed = false;
        notifs.forEach(n => {
          if (n && n.unread) {
            n.unread = false;
            changed = true;
          }
        });
        if (changed) {
          saveStoredNotifications(notifs);
        }
        renderNotifications();
        updateNotifBadge();
      }
    });

    // Close when clicking outside
    document.addEventListener('click', (e) => {
      if (notifDropdown && !notifDropdown.contains(e.target) && e.target !== notifBtn) {
        notifDropdown.classList.remove('show');
      }
    });

    // Clear notifications button
    document.addEventListener('click', (e) => {
      if (e.target && e.target.id === 'btn-clear-notifs') {
        saveStoredNotifications([]);
        renderNotifications();
        showToast('All notifications cleared.', 'info');
      }
    });
  }

  /* ============================================
     6. USER DROPDOWN TOGGLE & SIGN OUT
     ============================================ */
  const userProfileBtn = document.getElementById('user-profile-btn');
  const userDropdown = document.getElementById('user-dropdown');
  const sidebarSignoutBtn = document.getElementById('sidebar-signout-btn');
  const menuSignout = document.getElementById('menu-signout');

  if (userProfileBtn && userDropdown) {
    userProfileBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = userDropdown.classList.contains('show') || userDropdown.classList.contains('active');
      userDropdown.classList.toggle('show', !isOpen);
      userDropdown.classList.toggle('active', !isOpen);
      userProfileBtn.setAttribute('aria-expanded', !isOpen);
    });

    document.addEventListener('click', (e) => {
      if (!userDropdown.contains(e.target) && !userProfileBtn.contains(e.target)) {
        userDropdown.classList.remove('show');
        userDropdown.classList.remove('active');
        userProfileBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  async function handleSignOut(e) {
    if (e) e.preventDefault();
    try {
      if (typeof API !== 'undefined' && API.auth) {
        await API.auth.logout();
      }
    } catch (_) {}
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('username');
    localStorage.removeItem('userRole');
    showToast('Signed out successfully.', 'info');
    setTimeout(() => {
      window.location.href = 'login.html';
    }, 400);
  }

  if (sidebarSignoutBtn) {
    sidebarSignoutBtn.addEventListener('click', handleSignOut);
  }
  if (menuSignout) {
    menuSignout.addEventListener('click', handleSignOut);
  }

  /* ============================================
     7. CONTACT DIRECTORY (HOME.HTML)
     ============================================ */
  const contactCardsList = document.getElementById('contact-cards-list');
  const searchInput = document.getElementById('search-input');
  const deptDropdown = document.getElementById('dept-dropdown');
  const tabButtons = document.querySelectorAll('.tab-btn');
  const pageButtons = document.querySelectorAll('.page-num');
  const prevPageBtn = document.getElementById('prev-page-btn');
  const nextPageBtn = document.getElementById('next-page-btn');

  const badgeIcons = {
    Security: `
      <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        <polyline points="9 12 11 14 15 10"></polyline>
      </svg>`,
    Emergency: `
      <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="16"></line>
        <line x1="8" y1="12" x2="16" y2="12"></line>
      </svg>`,
    Medical: `
      <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
      </svg>`,
    Administration: `
      <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="7" r="4"></circle>
        <path d="M6 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"></path>
      </svg>`
  };

  // User-Managed Contact Directory Store
  function initContactStore() {
    const raw = localStorage.getItem('SiteSafety_Contacts');
    let contacts = [];
    if (raw) {
      try {
        contacts = JSON.parse(raw);
        if (!Array.isArray(contacts)) contacts = [];
      } catch (e) {
        console.error('Error parsing SiteSafety_Contacts:', e);
        contacts = [];
      }
    }

    // Purge mock contact seeds so only user-added contacts exist
    const mockNames = ['Michael Vance', 'Sarah Lin', 'Dr. Robert Hayes', 'Dr. Hayes', 'Angela Brooks', 'David Kim', 'Elena Gomez', 'Marcus Sterling', 'Jennifer Ward'];
    contacts = contacts.filter(c => c && c.name && !mockNames.includes(c.name));

    localStorage.setItem('SiteSafety_Contacts', JSON.stringify(contacts));
    return contacts;
  }

  function getStoredContacts() {
    return initContactStore();
  }

  function saveStoredContacts(contacts) {
    localStorage.setItem('SiteSafety_Contacts', JSON.stringify(contacts));
  }

  let currentDept = 'all';
  let searchQuery = '';
  let currentPage = 1;
  const itemsPerPage = 4;

  function renderContacts() {
    if (!contactCardsList) return;

    const contactsData = getStoredContacts();

    const filtered = contactsData.filter((item) => {
      const matchDept = currentDept === 'all' || (item.dept && item.dept.toLowerCase() === currentDept.toLowerCase());
      const query = searchQuery.toLowerCase().trim();
      const matchSearch =
        !query ||
        (item.name && item.name.toLowerCase().includes(query)) ||
        (item.position && item.position.toLowerCase().includes(query)) ||
        (item.phone && item.phone.toLowerCase().includes(query)) ||
        (item.email && item.email.toLowerCase().includes(query)) ||
        (item.dept && item.dept.toLowerCase().includes(query));

      return matchDept && matchSearch;
    });

    const totalPages = Math.max(1, Math.ceil(filtered.length / itemsPerPage));
    if (currentPage > totalPages) currentPage = totalPages;

    const startIndex = (currentPage - 1) * itemsPerPage;
    const paginatedItems = filtered.slice(startIndex, startIndex + itemsPerPage);

    if (paginatedItems.length === 0) {
      if (contactsData.length === 0) {
        contactCardsList.innerHTML = `
          <div class="contact-empty-state">
            <svg class="contact-empty-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            <div class="contact-empty-title">No Contacts in Directory</div>
            <div class="contact-empty-subtitle">Click "+ Add Contact" above to add your team members to the directory.</div>
          </div>
        `;
      } else {
        contactCardsList.innerHTML = `
          <div class="no-results">
            <p>No contacts found matching your search or filter criteria.</p>
          </div>
        `;
      }
    } else {
      contactCardsList.innerHTML = paginatedItems
        .map((contact, idx) => {
          const badgeClass = `badge-${(contact.dept || 'security').toLowerCase()}`;
          const icon = badgeIcons[contact.dept] || badgeIcons['Security'];

          return `
            <div class="contact-card">
              <div class="cell-name-position">
                <span class="contact-name">${escapeHTML(contact.name)}</span>
                <span class="contact-position">${escapeHTML(contact.position)}</span>
              </div>
              <div class="contact-phone">${escapeHTML(contact.phone)}</div>
              <div class="contact-email">${escapeHTML(contact.email)}</div>
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                <span class="badge-dept ${badgeClass}">
                  ${icon}
                  ${escapeHTML(contact.dept)}
                </span>
                <button type="button" class="contact-delete-btn" data-contact-id="${escapeHTML(contact.id || '')}" data-index="${startIndex + idx}" title="Delete contact" aria-label="Delete contact">
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                </button>
              </div>
            </div>
          `;
        })
        .join('');
    }

    if (prevPageBtn) prevPageBtn.disabled = currentPage <= 1;
    if (nextPageBtn) nextPageBtn.disabled = currentPage >= totalPages;

    pageButtons.forEach((btn) => {
      const pageNum = parseInt(btn.getAttribute('data-page'), 10);
      btn.classList.toggle('active', pageNum === currentPage);
      btn.style.display = pageNum <= totalPages ? 'flex' : 'none';
    });
  }

  if (searchInput && contactCardsList) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value;
      currentPage = 1;
      renderContacts();
    });
  }

  tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      tabButtons.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');

      const dept = btn.getAttribute('data-dept');
      currentDept = dept;
      if (deptDropdown) deptDropdown.value = dept;

      currentPage = 1;
      renderContacts();
    });
  });

  if (deptDropdown) {
    deptDropdown.addEventListener('change', (e) => {
      const dept = e.target.value;
      currentDept = dept;

      tabButtons.forEach((btn) => {
        btn.classList.toggle('active', btn.getAttribute('data-dept').toLowerCase() === dept.toLowerCase());
      });

      currentPage = 1;
      renderContacts();
    });
  }

  if (prevPageBtn && contactCardsList) {
    prevPageBtn.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        renderContacts();
      }
    });
  }

  if (nextPageBtn && contactCardsList) {
    nextPageBtn.addEventListener('click', () => {
      currentPage++;
      renderContacts();
    });
  }

  // Handle contact deletion
  if (contactCardsList) {
    contactCardsList.addEventListener('click', (e) => {
      const delBtn = e.target.closest('.contact-delete-btn');
      if (delBtn) {
        const contactId = delBtn.getAttribute('data-contact-id');
        let contacts = getStoredContacts();
        if (contactId) {
          contacts = contacts.filter(c => c.id !== contactId);
        } else {
          const contactIndex = parseInt(delBtn.getAttribute('data-index'), 10);
          if (!isNaN(contactIndex) && contactIndex >= 0 && contactIndex < contacts.length) {
            contacts.splice(contactIndex, 1);
          }
        }
        saveStoredContacts(contacts);
        if (window.API && window.API.contacts && typeof window.API.contacts.delete === 'function' && contactId) {
          window.API.contacts.delete(contactId).catch(e => console.warn('Sync delete contact to DB:', e.message));
        }
        renderContacts();
        showToast('Contact removed from directory.', 'info');
      }
    });

    renderContacts();
  }

  // Handle Add Contact Modal
  const openAddContactModalBtn = document.getElementById('open-add-contact-modal-btn');
  const addContactModal = document.getElementById('add-contact-modal');
  const closeAddContactModalBtn = document.getElementById('close-add-contact-modal-btn');
  const cancelAddContactBtn = document.getElementById('cancel-add-contact-btn');
  const addContactForm = document.getElementById('add-contact-form');

  if (openAddContactModalBtn && addContactModal) {
    openAddContactModalBtn.addEventListener('click', () => {
      addContactModal.style.display = 'flex';
      const firstInput = document.getElementById('contact-name-input');
      if (firstInput) firstInput.focus();
    });

    const closeModal = () => {
      addContactModal.style.display = 'none';
      if (addContactForm) addContactForm.reset();
    };

    if (closeAddContactModalBtn) closeAddContactModalBtn.addEventListener('click', closeModal);
    if (cancelAddContactBtn) cancelAddContactBtn.addEventListener('click', closeModal);

    addContactModal.addEventListener('click', (e) => {
      if (e.target === addContactModal) closeModal();
    });

    if (addContactForm) {
      addContactForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const name = (document.getElementById('contact-name-input')?.value || '').trim();
        const position = (document.getElementById('contact-pos-input')?.value || '').trim();
        const phone = (document.getElementById('contact-phone-input')?.value || '').trim();
        const email = (document.getElementById('contact-email-input')?.value || '').trim();
        const dept = document.getElementById('contact-dept-input')?.value || 'Security';

        if (!name || !position || !phone || !email) {
          showToast('Please fill in all contact fields.', 'error');
          return;
        }

        const newContact = {
          id: 'contact-' + Date.now(),
          name,
          position,
          phone,
          email,
          dept
        };

        const contacts = getStoredContacts();
        contacts.unshift(newContact);
        saveStoredContacts(contacts);
        if (window.API && window.API.contacts && typeof window.API.contacts.create === 'function') {
          window.API.contacts.create(newContact).catch(e => console.warn('Sync contact to DB:', e.message));
        }
        closeModal();
        renderContacts();
        showToast(`Contact "${name}" added to directory.`, 'success');
      });
    }
  }

  /* ============================================
     8. CREATE REPORT / HAZARD FORM & PHOTO EVIDENCE
     ============================================ */
  const urgencyPills = document.querySelectorAll('.urgency-pill');
  let selectedUrgency = 'Low';

  urgencyPills.forEach((pill) => {
    pill.addEventListener('click', () => {
      urgencyPills.forEach((p) => p.classList.remove('active'));
      pill.classList.add('active');
      selectedUrgency = pill.getAttribute('data-urgency');
    });
  });

  const photoInput = document.getElementById('report-photo-input');
  const photoPreviewBox = document.getElementById('photo-preview-box');
  const photoPreviewImg = document.getElementById('photo-preview-img');
  let attachedPhotoDataUrl = '';

  if (photoInput) {
    photoInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        // Size validation (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
          showToast('Image file too large. Please select an image under 5MB.', 'error');
          photoInput.value = '';
          return;
        }

        const reader = new FileReader();
        reader.onload = (uploadEvent) => {
          attachedPhotoDataUrl = uploadEvent.target.result;
          if (photoPreviewImg) photoPreviewImg.src = attachedPhotoDataUrl;
          if (photoPreviewBox) photoPreviewBox.style.display = 'block';
          showToast('Photo evidence attached!', 'info');
        };
        reader.readAsDataURL(file);
      } else {
        attachedPhotoDataUrl = '';
        if (photoPreviewBox) photoPreviewBox.style.display = 'none';
      }
    });
  }

  const reportForm = document.getElementById('hazard-report-form');
  const cancelReportBtn = document.getElementById('btn-cancel-report');

  if (reportForm) {
    reportForm.addEventListener('submit', (e) => {
      e.preventDefault();

      const location = document.getElementById('report-location')?.value.trim();
      const date = document.getElementById('report-date')?.value.trim();
      const time = document.getElementById('report-time')?.value.trim();
      const category = document.getElementById('report-category')?.value;
      const cause = document.getElementById('report-cause')?.value.trim();
      const phone = document.getElementById('personnel-phone')?.value.trim();
      const position = document.getElementById('personnel-position')?.value.trim();
      const name = document.getElementById('personnel-name')?.value.trim();
      const dept = document.getElementById('personnel-dept')?.value.trim();

      // Generate Ticket Number: ABC-2026-MMDD-XX
      const now = new Date();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      const randomSuffix = String(Math.floor(10 + Math.random() * 90));
      const ticketNumber = `ABC-2026-${mm}${dd}-${randomSuffix}`;

      const reportData = {
        ticket: ticketNumber,
        location: location || 'West Wing Construction - Sector 4',
        date: date || `${mm}-${dd}-26`,
        time: time || now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        category: category || 'Structural Hazard',
        cause: cause || 'Scaffolding connection joints loosened under gusty weather conditions.',
        urgency: selectedUrgency,
        status: 'Pending',
        photo: attachedPhotoDataUrl || '',
        personnel: {
          phone: phone || '+1 (555) 019-2834',
          position: position || 'Lead Safety Officer',
          name: name || 'Andrei Santos',
          dept: dept || 'Security / Safety'
        },
        timestamp: now.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) + ' | ' + (time || now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
      };

      // Persist to lastSubmittedReport
      localStorage.setItem('lastSubmittedReport', JSON.stringify(reportData));

      // Append into SiteSafety_Hazards shared store
      const allHazards = getStoredHazards();
      allHazards.unshift(reportData);
      saveStoredHazards(allHazards);

      // Record to SQLite database
      if (window.API && window.API.hazards && typeof window.API.hazards.create === 'function') {
        window.API.hazards.create(reportData).catch(e => console.warn('Sync hazard to DB:', e.message));
      }

      // Add system activity notification
      addNotification(`New Hazard Filed: ${reportData.ticket} (${reportData.category})`, { ticket: reportData.ticket });

      showToast(`Report ${ticketNumber} created successfully! Redirecting...`, 'success');
      setTimeout(() => {
        window.location.href = 'report-status.html';
      }, 700);
    });
  }

  if (cancelReportBtn) {
    cancelReportBtn.addEventListener('click', () => {
      window.location.href = 'home.html';
    });
  }

  /* ============================================
     9. STEP 2: REPORT STATUS & PRINTING
     ============================================ */
  const docSite = document.getElementById('doc-site');
  const btnSubmitAnother = document.getElementById('btn-submit-another-page');
  const btnStatusDone = document.getElementById('btn-status-done');
  const btnStatusCancel = document.getElementById('btn-status-cancel');
  const docPhotoContainer = document.getElementById('doc-photo-container');

  if (docSite) {
    const rawData = localStorage.getItem('lastSubmittedReport');
    if (rawData) {
      try {
        const data = JSON.parse(rawData);
        if (data.location) docSite.textContent = data.location;
        if (data.date && data.time) {
          const dt = `${data.date} | ${data.time}`;
          const el = document.getElementById('doc-datetime');
          if (el) el.textContent = dt;
        }
        if (data.category) {
          const elCat = document.getElementById('doc-category');
          const elCatDesc = document.getElementById('doc-cat-desc');
          if (elCat) elCat.textContent = data.category;
          if (elCatDesc) elCatDesc.textContent = data.category;
        }
        if (data.urgency) {
          const elUrg = document.getElementById('doc-urgency');
          if (elUrg) {
            elUrg.textContent = data.urgency;
            elUrg.style.color = data.urgency === 'Critical' ? '#b91c1c' : data.urgency === 'Medium' || data.urgency === 'High' ? '#a67302' : '#1b7a43';
          }
        }
        if (data.cause) {
          const elCause = document.getElementById('doc-cause');
          if (elCause) elCause.textContent = data.cause;
        }
        if (data.personnel) {
          if (data.personnel.name) {
            const elName = document.getElementById('doc-rep-name');
            if (elName) elName.textContent = data.personnel.name;
          }
          if (data.personnel.position) {
            const elPos = document.getElementById('doc-rep-pos');
            if (elPos) elPos.textContent = data.personnel.position;
          }
          if (data.personnel.dept) {
            const elDept = document.getElementById('doc-rep-dept');
            if (elDept) elDept.textContent = data.personnel.dept;
          }
        }
        if (data.timestamp) {
          const elTs = document.getElementById('status-submission-timestamp');
          if (elTs) elTs.textContent = data.timestamp;
        }

        // Render Photo Evidence if attached
        if (data.photo && docPhotoContainer) {
          docPhotoContainer.innerHTML = `<img src="${data.photo}" alt="Attached Hazard Photo" style="max-height: 80px; object-fit: cover; border-radius: 3px;">`;
        }
      } catch (err) {
        console.error('Error parsing submitted report data:', err);
      }
    }

    if (btnSubmitAnother) {
      btnSubmitAnother.addEventListener('click', () => {
        window.location.href = 'create-report.html';
      });
    }

    if (btnStatusDone) {
      btnStatusDone.addEventListener('click', () => {
        window.location.href = 'home.html';
      });
    }

    if (btnStatusCancel) {
      btnStatusCancel.addEventListener('click', () => {
        window.location.href = 'home.html';
      });
    }
  }

  /* ============================================
     10. REPORT HISTORY (STAFF AUDIT LOG)
     ============================================ */
  const historyCardsContainer = document.getElementById('history-cards-list');
  const historySearchInput = document.getElementById('history-search-input');
  const filterLocation = document.getElementById('filter-location');
  const filterCategory = document.getElementById('filter-category');
  const filterStatus = document.getElementById('filter-status');
  const filterDate = document.getElementById('filter-date');
  const btnViewAllReports = document.getElementById('btn-view-all-reports');
  const btnExportHistoryCsv = document.getElementById('btn-export-history-csv');
  const historyPagination = document.querySelector('.main-content #pagination');

  if (historyCardsContainer) {
    let currentHistoryPage = 1;
    const historyPerPage = 5;

    function renderHistoryList() {
      const allHazards = getStoredHazards();
      const q = (historySearchInput?.value || '').toLowerCase().trim();
      const locVal = filterLocation?.value || 'all';
      const catVal = filterCategory?.value || 'all';
      const statusVal = filterStatus?.value || 'all';

      const filtered = allHazards.filter((item) => {
        const textToSearch = `${item.ticket} ${item.location} ${item.category} ${item.cause || ''}`.toLowerCase();
        const matchQ = !q || textToSearch.includes(q);
        const matchLoc = locVal === 'all' || item.location.toLowerCase().includes(locVal.toLowerCase());
        const matchCat = catVal === 'all' || item.category.toLowerCase().includes(catVal.toLowerCase());
        const matchStatus = statusVal === 'all' || item.status.toLowerCase() === statusVal.toLowerCase();

        return matchQ && matchLoc && matchCat && matchStatus;
      });

      const totalPages = Math.max(1, Math.ceil(filtered.length / historyPerPage));
      if (currentHistoryPage > totalPages) currentHistoryPage = totalPages;

      const startIndex = (currentHistoryPage - 1) * historyPerPage;
      const pageItems = filtered.slice(startIndex, startIndex + historyPerPage);

      if (pageItems.length === 0) {
        historyCardsContainer.innerHTML = `
          <div style="text-align: center; padding: 40px; font-weight: 600; color: #555; background: #ffffff; border-radius: 8px; border: 1.5px solid var(--border-input);">
            No incident reports found matching the selected filters.
          </div>`;
      } else {
        historyCardsContainer.innerHTML = pageItems
          .map((item, index) => {
            const bgClass = index % 2 === 0 ? 'row-white' : 'row-blue';
            const statusClass = item.status === 'Resolved' ? 'status-resolved' : item.status === 'In progress' ? 'status-in-progress' : 'status-under-review';

            return `
              <div class="history-row-card ${bgClass}">
                <div class="cell-ticket">
                  <svg class="folder-icon" viewBox="0 0 24 24">
                    <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
                  </svg>
                  <a href="report-status.html" class="ticket-link" data-ticket="${escapeHTML(item.ticket)}">${escapeHTML(item.ticket)}</a>
                </div>
                <div class="cell-location">
                  <svg viewBox="0 0 24 24">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                    <circle cx="12" cy="10" r="3"></circle>
                  </svg>
                  <span>${escapeHTML(item.location)}</span>
                </div>
                <div class="cell-category">${escapeHTML(item.category)}</div>
                <div class="cell-date">
                  <svg viewBox="0 0 24 24">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                    <line x1="16" y1="2" x2="16" y2="6"></line>
                    <line x1="8" y1="2" x2="8" y2="6"></line>
                    <line x1="3" y1="10" x2="21" y2="10"></line>
                  </svg>
                  <div class="date-text-group">
                    <span class="date-main">${escapeHTML(item.date)}</span>
                    <span class="date-sub">${escapeHTML(item.time)}</span>
                  </div>
                </div>
                <div>
                  <span class="status-pill ${statusClass}">${escapeHTML(item.status)}</span>
                </div>
              </div>
            `;
          })
          .join('');

        // Wire ticket links to set lastSubmittedReport so review page renders this ticket
        historyCardsContainer.querySelectorAll('.ticket-link').forEach((link) => {
          link.addEventListener('click', () => {
            const ticketId = link.getAttribute('data-ticket');
            const found = allHazards.find(h => h.ticket === ticketId);
            if (found) {
              localStorage.setItem('lastSubmittedReport', JSON.stringify(found));
            }
          });
        });
      }

      // Update Pagination UI
      if (historyPagination) {
        const prevBtn = historyPagination.querySelector('#prev-page-btn');
        const nextBtn = historyPagination.querySelector('#next-page-btn');
        if (prevBtn) prevBtn.disabled = currentHistoryPage <= 1;
        if (nextBtn) nextBtn.disabled = currentHistoryPage >= totalPages;

        const pageBtns = historyPagination.querySelectorAll('.page-num');
        pageBtns.forEach((btn) => {
          const p = parseInt(btn.getAttribute('data-page'), 10);
          btn.classList.toggle('active', p === currentHistoryPage);
          btn.style.display = p <= totalPages ? 'flex' : 'none';
        });
      }
    }

    if (historySearchInput) historySearchInput.addEventListener('input', () => { currentHistoryPage = 1; renderHistoryList(); });
    if (filterLocation) filterLocation.addEventListener('change', () => { currentHistoryPage = 1; renderHistoryList(); });
    if (filterCategory) filterCategory.addEventListener('change', () => { currentHistoryPage = 1; renderHistoryList(); });
    if (filterStatus) filterStatus.addEventListener('change', () => { currentHistoryPage = 1; renderHistoryList(); });
    if (filterDate) filterDate.addEventListener('change', () => { currentHistoryPage = 1; renderHistoryList(); });

    if (btnViewAllReports) {
      btnViewAllReports.addEventListener('click', () => {
        if (historySearchInput) historySearchInput.value = '';
        if (filterLocation) filterLocation.value = 'all';
        if (filterCategory) filterCategory.value = 'all';
        if (filterStatus) filterStatus.value = 'all';
        if (filterDate) filterDate.value = 'all';
        currentHistoryPage = 1;
        renderHistoryList();
      });
    }

    if (historyPagination) {
      const prevBtn = historyPagination.querySelector('#prev-page-btn');
      const nextBtn = historyPagination.querySelector('#next-page-btn');
      const pageBtns = historyPagination.querySelectorAll('.page-num');

      if (prevBtn) {
        prevBtn.addEventListener('click', () => {
          if (currentHistoryPage > 1) {
            currentHistoryPage--;
            renderHistoryList();
          }
        });
      }

      if (nextBtn) {
        nextBtn.addEventListener('click', () => {
          currentHistoryPage++;
          renderHistoryList();
        });
      }

      pageBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
          const p = parseInt(btn.getAttribute('data-page'), 10);
          if (!isNaN(p)) {
            currentHistoryPage = p;
            renderHistoryList();
          }
        });
      });
    }

    // Export CSV Handler
    if (btnExportHistoryCsv) {
      btnExportHistoryCsv.addEventListener('click', () => {
        const allHazards = getStoredHazards();
        exportToCSV('SiteSafety_Incident_History.csv', allHazards, [
          { label: 'Ticket Number', key: 'ticket' },
          { label: 'Location', key: 'location' },
          { label: 'Category', key: 'category' },
          { label: 'Date', key: 'date' },
          { label: 'Time', key: 'time' },
          { label: 'Urgency', key: 'urgency' },
          { label: 'Status', key: 'status' },
          { label: 'Incident Cause', key: 'cause' },
          { label: 'Reported By', key: (h) => h.personnel?.name || '' }
        ]);
      });
    }

    renderHistoryList();
  }

  /* ============================================
     11. DASHBOARD & INSPECTION TIMETABLE
     ============================================ */
  const dashboardRowsList = document.querySelector('.dashboard-rows-list');
  const dashboardPagination = document.querySelector('.dashboard-outer-card #pagination');

  if (dashboardRowsList && dashboardPagination) {
    let currentInspPage = 1;
    const inspPerPage = 6;

    function renderDashboardInspections() {
      const inspectionsData = getStoredInspections();
      const totalInspPages = Math.max(1, Math.ceil(inspectionsData.length / inspPerPage));
      if (currentInspPage > totalInspPages) currentInspPage = totalInspPages;

      const startIndex = (currentInspPage - 1) * inspPerPage;
      const currentItems = inspectionsData.slice(startIndex, startIndex + inspPerPage);

      dashboardRowsList.innerHTML = currentItems
        .map((item, index) => {
          const bgClass = index % 2 === 0 ? 'dashboard-row-white' : 'dashboard-row-blue';
          return `
            <div class="dashboard-row-card ${bgClass}">
              <div class="cell-inspection">
                <svg class="folder-icon" viewBox="0 0 24 24">
                  <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
                </svg>
                <span>${escapeHTML(item.title)}</span>
              </div>
              <div class="cell-location">
                <svg viewBox="0 0 24 24">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                  <circle cx="12" cy="10" r="3"></circle>
                </svg>
                <span>${escapeHTML(item.location)}</span>
              </div>
              <div class="cell-inspector">${escapeHTML(item.inspector)}</div>
              <div class="cell-date">
                <svg viewBox="0 0 24 24">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="16" y1="2" x2="16" y2="6"></line>
                  <line x1="8" y1="2" x2="8" y2="6"></line>
                  <line x1="3" y1="10" x2="21" y2="10"></line>
                </svg>
                <div class="date-text-group">
                  <span class="date-main">${escapeHTML(item.date)}</span>
                  <span class="date-sub">${escapeHTML(item.time)}</span>
                </div>
              </div>
              <div class="cell-status-action">
                <span class="status-label-scheduled">${escapeHTML(item.status)}</span>
                <button type="button" class="btn-view-inspection" data-index="${startIndex + index}">View</button>
              </div>
            </div>
          `;
        })
        .join('');

      // Attach view button toast details
      dashboardRowsList.querySelectorAll('.btn-view-inspection').forEach((btn) => {
        btn.addEventListener('click', () => {
          const idx = parseInt(btn.getAttribute('data-index'), 10);
          const item = inspectionsData[idx];
          if (item) {
            showToast(`Inspection: "${item.title}" scheduled for ${item.date} (${item.time}) at ${item.location} by ${item.inspector}.`, 'info', 5000);
          }
        });
      });

      // Update pagination buttons
      const prevBtn = dashboardPagination.querySelector('#prev-page-btn');
      const nextBtn = dashboardPagination.querySelector('#next-page-btn');
      if (prevBtn) prevBtn.disabled = currentInspPage <= 1;
      if (nextBtn) nextBtn.disabled = currentInspPage >= totalInspPages;

      const pageButtons = dashboardPagination.querySelectorAll('.page-num');
      pageButtons.forEach((btn) => {
        const pageNum = parseInt(btn.getAttribute('data-page'), 10);
        btn.classList.toggle('active', pageNum === currentInspPage);
        btn.style.display = pageNum <= totalInspPages ? 'flex' : 'none';
      });
    }

    // Expose global helper for adding inspections dynamically
    window.addInspectionItem = function(newItem) {
      // 1. Save to Inspections Store
      const inspections = getStoredInspections();
      inspections.unshift(newItem);
      saveStoredInspections(inspections);

      // 2. Reflect directly into Pending Hazards Store
      const now = new Date();
      const mm = String(now.getMonth() + 1).padStart(2, '0');
      const dd = String(now.getDate()).padStart(2, '0');
      const yy = String(now.getFullYear()).slice(-2);
      const randNum = Math.floor(10 + Math.random() * 90);
      const inspTicket = `INSP-2026-${mm}${dd}-${randNum}`;

      const inspectionHazard = {
        ticket: inspTicket,
        location: newItem.location || 'Construction Site',
        category: 'Site Inspection',
        date: newItem.date || `${mm}-${dd}-${yy}`,
        time: newItem.time || now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        urgency: 'Medium',
        status: 'Pending',
        cause: `Scheduled Site Inspection: "${newItem.title}" assigned to inspector ${newItem.inspector}. Inspection checklist and safety assessment pending on-site completion.`,
        photo: '',
        personnel: {
          name: newItem.inspector || 'Safety Inspector',
          position: 'Certified Safety Inspector',
          phone: '+1 (555) 019-2834',
          dept: 'Safety Inspection & Compliance'
        },
        timestamp: now.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) + ' | ' + (newItem.time || now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))
      };

      const allHazards = getStoredHazards();
      allHazards.unshift(inspectionHazard);
      saveStoredHazards(allHazards);

      // 3. Reflect strictly to database (both inspections and hazards tables)
      if (window.API) {
        if (window.API.inspections && typeof window.API.inspections.create === 'function') {
          window.API.inspections.create(newItem).catch(e => console.warn('Sync inspection to DB:', e.message));
        }
        if (window.API.hazards && typeof window.API.hazards.create === 'function') {
          window.API.hazards.create(inspectionHazard).catch(e => console.warn('Sync inspection hazard to DB:', e.message));
        }
      }

      addNotification(`New Inspection Scheduled: ${newItem.title} (Pending Ticket: ${inspTicket})`, { ticket: inspTicket, url: 'manager-home.html' });
      currentInspPage = 1;
      renderDashboardInspections();
    };
    window.renderDashboardInspections = renderDashboardInspections;

    const prevBtn = dashboardPagination.querySelector('#prev-page-btn');
    const nextBtn = dashboardPagination.querySelector('#next-page-btn');
    const pageButtons = dashboardPagination.querySelectorAll('.page-num');

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (currentInspPage > 1) {
          currentInspPage--;
          renderDashboardInspections();
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        currentInspPage++;
        renderDashboardInspections();
      });
    }

    pageButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const pageNum = parseInt(btn.getAttribute('data-page'), 10);
        if (!isNaN(pageNum)) {
          currentInspPage = pageNum;
          renderDashboardInspections();
        }
      });
    });

    renderDashboardInspections();
  }

  /* ============================================
     12. SETTINGS TAB & CANVA CONFIRMATION MODAL
     ============================================ */
  const settingsName = document.getElementById('settings-name');
  const settingsUsername = document.getElementById('settings-username');
  const settingsEmail = document.getElementById('settings-email');
  const settingsCompany = document.getElementById('settings-company');
  const profileDisplayName = document.getElementById('profile-display-name');
  const profileDisplayMeta = document.getElementById('profile-display-meta');
  const avatarFileInput = document.getElementById('avatar-file-input');
  const avatarDisplay = document.getElementById('settings-avatar-display');
  const btnEditAvatar = document.getElementById('btn-edit-avatar');
  const settingsForm = document.getElementById('settings-form');
  const settingsPasswordForm = document.getElementById('settings-password-form');
  const btnSaveNotifications = document.getElementById('btn-save-notifications');

  const btnOpenDeleteModal = document.getElementById('btn-open-delete-modal');
  const deleteModalBackdrop = document.getElementById('delete-modal-backdrop');
  const btnModalConfirmDelete = document.getElementById('btn-modal-confirm-delete');
  const btnModalCancel = document.getElementById('btn-modal-cancel');

  // Tab switching logic
  const settingsTabButtons = document.querySelectorAll('.settings-tab-btn');
  const settingsTabPanes = document.querySelectorAll('.settings-tab-pane');

  if (settingsTabButtons.length > 0) {
    settingsTabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTabId = btn.getAttribute('data-tab');
        
        settingsTabButtons.forEach(b => {
          b.classList.remove('active');
          b.setAttribute('aria-selected', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');

        settingsTabPanes.forEach(pane => {
          if (pane.id === targetTabId) {
            pane.style.display = 'block';
            pane.classList.add('active');
          } else {
            pane.style.display = 'none';
            pane.classList.remove('active');
          }
        });
      });
    });
  }

  // Populate Profile form data
  if (settingsEmail) {
    const savedEmail = localStorage.getItem('userEmail') || (selectedRole === 'manager' ? 'manager@sitesafety.com' : 'andrei@sitesafety.com');
    const rawUsername = localStorage.getItem('userUsername') || savedEmail.split('@')[0];
    const defaultName = rawUsername.charAt(0).toUpperCase() + rawUsername.slice(1);
    const savedName = localStorage.getItem('userName') || (selectedRole === 'manager' ? 'Safety Manager Andrei' : defaultName);
    const savedCompany = localStorage.getItem('userCompany') || 'Apex Construction Ltd.';
    const savedAvatar = localStorage.getItem('userAvatar');

    if (settingsName) settingsName.value = savedName;
    if (settingsUsername) settingsUsername.value = rawUsername;
    settingsEmail.value = savedEmail;
    if (settingsCompany) settingsCompany.value = savedCompany;

    if (profileDisplayName) profileDisplayName.textContent = savedName;
    if (profileDisplayMeta) profileDisplayMeta.innerHTML = `${savedCompany} • <span class="badge-role-mini">Active</span>`;

    if (savedAvatar && avatarDisplay) {
      avatarDisplay.innerHTML = `<img src="${savedAvatar}" alt="Profile avatar">`;
    }
  }

  // Avatar upload simulation with local storage preview
  if (btnEditAvatar && avatarFileInput) {
    btnEditAvatar.addEventListener('click', () => {
      avatarFileInput.click();
    });

    avatarFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        if (file.size > 2 * 1024 * 1024) {
          showToast('Image file too large (max 2MB).', 'warning');
          return;
        }
        const reader = new FileReader();
        reader.onload = (evt) => {
          const dataUrl = evt.target.result;
          localStorage.setItem('userAvatar', dataUrl);
          if (avatarDisplay) {
            avatarDisplay.innerHTML = `<img src="${dataUrl}" alt="Profile avatar">`;
          }
          showToast('Profile picture updated successfully!', 'success');
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // Save Profile Form
  if (settingsForm) {
    settingsForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const updatedName = settingsName ? settingsName.value.trim() : '';
      const updatedUsername = settingsUsername ? settingsUsername.value.trim() : '';
      const updatedEmail = settingsEmail ? settingsEmail.value.trim() : '';
      const updatedCompany = settingsCompany ? settingsCompany.value.trim() : '';

      if (!updatedName || !updatedEmail) {
        showToast('Name and Email are required fields.', 'warning');
        return;
      }

      localStorage.setItem('userName', updatedName);
      if (updatedUsername) localStorage.setItem('userUsername', updatedUsername);
      localStorage.setItem('userEmail', updatedEmail);
      if (updatedCompany) localStorage.setItem('userCompany', updatedCompany);

      if (profileDisplayName) profileDisplayName.textContent = updatedName;
      if (profileDisplayMeta) profileDisplayMeta.innerHTML = `${updatedCompany || 'SiteSafety Systems'} • <span class="badge-role-mini">Active</span>`;
      
      const displayAccountName = document.getElementById('display-account-name');
      if (displayAccountName) displayAccountName.textContent = updatedName;

      showToast('Profile settings saved successfully!', 'success');
    });
  }

  // Password Update Form
  if (settingsPasswordForm) {
    settingsPasswordForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const currentPass = document.getElementById('current-password')?.value || '';
      const newPass = document.getElementById('new-password')?.value || '';
      const confirmPass = document.getElementById('confirm-password')?.value || '';

      if (!currentPass) {
        showToast('Please enter your current password.', 'warning');
        return;
      }
      if (newPass.length < 8) {
        showToast('New password must be at least 8 characters.', 'warning');
        return;
      }
      if (newPass !== confirmPass) {
        showToast('New passwords do not match.', 'error');
        return;
      }

      document.getElementById('current-password').value = '';
      document.getElementById('new-password').value = '';
      document.getElementById('confirm-password').value = '';
      showToast('Password updated successfully!', 'success');
    });
  }

  // Save Notifications
  if (btnSaveNotifications) {
    btnSaveNotifications.addEventListener('click', () => {
      const inc = document.getElementById('notif-incidents')?.checked;
      const insp = document.getElementById('notif-inspections')?.checked;
      const em = document.getElementById('notif-email')?.checked;

      localStorage.setItem('pref_notif_incidents', inc ? 'true' : 'false');
      localStorage.setItem('pref_notif_inspections', insp ? 'true' : 'false');
      localStorage.setItem('pref_notif_email', em ? 'true' : 'false');

      showToast('Notification preferences saved!', 'success');
    });
  }

  // Delete Confirmation Modal
  if (btnOpenDeleteModal && deleteModalBackdrop) {
    btnOpenDeleteModal.addEventListener('click', () => {
      deleteModalBackdrop.classList.add('show');
    });

    if (btnModalCancel) {
      btnModalCancel.addEventListener('click', () => {
        deleteModalBackdrop.classList.remove('show');
      });
    }

    deleteModalBackdrop.addEventListener('click', (e) => {
      if (e.target === deleteModalBackdrop) {
        deleteModalBackdrop.classList.remove('show');
      }
    });

    if (btnModalConfirmDelete) {
      btnModalConfirmDelete.addEventListener('click', () => {
        localStorage.clear();
        showToast('Your account and profile records have been deleted.', 'error');
        setTimeout(() => {
          window.location.href = 'index.html';
        }, 900);
      });
    }
  }

  /* ============================================
     13. MANAGER PENDING HAZARDS & DETAIL ACTIONS
     ============================================ */
  const managerHazardsList = document.getElementById('manager-hazards-list');
  const managerPagination = document.getElementById('manager-pagination');
  const managerListView = document.getElementById('manager-list-view');
  const managerDetailView = document.getElementById('manager-detail-view');
  const managerSearchInput = document.getElementById('manager-search-input');
  const managerUrgencyFilter = document.getElementById('manager-urgency-filter');

  const detailTicketNumber = document.getElementById('detail-ticket-number');
  const detailLocation = document.getElementById('detail-location');
  const detailCategory = document.getElementById('detail-category');
  const detailDateMain = document.getElementById('detail-date-main');
  const detailDateSub = document.getElementById('detail-date-sub');
  const detailPhotoRow = document.getElementById('detail-photo-row');
  const detailPhotoImg = document.getElementById('detail-photo-img');
  const btnHazardResolved = document.getElementById('btn-hazard-resolved');
  const btnHazardCancel = document.getElementById('btn-hazard-cancel');

  let currentManagerPage = 1;
  const managerItemsPerPage = 6;
  let activeHazardTicket = null;

  function renderPendingHazards() {
    if (!managerHazardsList) return;

    const allHazards = getStoredHazards();
    const query = (managerSearchInput?.value || '').toLowerCase().trim();
    const urgencyVal = managerUrgencyFilter?.value || 'all';

    const pendingList = allHazards.filter(h => {
      if (h.status !== 'Pending') return false;
      const text = `${h.ticket} ${h.location} ${h.category}`.toLowerCase();
      const matchQ = !query || text.includes(query);
      const matchU = urgencyVal === 'all' || h.urgency?.toLowerCase() === urgencyVal.toLowerCase();
      return matchQ && matchU;
    });

    managerHazardsList.innerHTML = '';
    const totalPages = Math.max(1, Math.ceil(pendingList.length / managerItemsPerPage));
    if (currentManagerPage > totalPages) currentManagerPage = totalPages;

    const startIndex = (currentManagerPage - 1) * managerItemsPerPage;
    const pageItems = pendingList.slice(startIndex, startIndex + managerItemsPerPage);

    if (pageItems.length === 0) {
      managerHazardsList.innerHTML = `
        <div style="text-align: center; padding: 40px; font-weight: 600; color: #555;">
          No pending hazards found. All current workplace hazards are resolved!
        </div>`;
    } else {
      pageItems.forEach((item, index) => {
        const isBlue = (index % 2 === 1);
        const rowClass = isBlue ? 'hazard-row-blue' : 'hazard-row-white';

        const row = document.createElement('div');
        row.className = `manager-hazard-row ${rowClass}`;
        row.innerHTML = `
          <div class="cell-ticket">
            <svg viewBox="0 0 24 24">
              <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/>
            </svg>
            <span>${escapeHTML(item.ticket)}</span>
          </div>
          <div class="cell-location">
            <svg viewBox="0 0 24 24">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>
            <span>${escapeHTML(item.location)}</span>
          </div>
          <div class="cell-category">${escapeHTML(item.category)}</div>
          <div class="cell-date">
            <svg viewBox="0 0 24 24">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="16" y1="2" x2="16" y2="6"></line>
              <line x1="8" y1="2" x2="8" y2="6"></line>
              <line x1="3" y1="10" x2="21" y2="10"></line>
            </svg>
            <div class="date-text-group">
              <span class="date-main">${escapeHTML(item.date)}</span>
              <span class="date-sub">${escapeHTML(item.time)}</span>
            </div>
          </div>
          <div class="cell-urgency">${escapeHTML(item.urgency || 'Medium')}</div>
          <div class="cell-action">
            <button type="button" class="btn-view-hazard" data-ticket="${escapeHTML(item.ticket)}">View</button>
          </div>
        `;

        const viewBtn = row.querySelector('.btn-view-hazard');
        viewBtn.addEventListener('click', () => {
          openHazardDetail(item);
        });

        managerHazardsList.appendChild(row);
      });
    }

    if (managerPagination) {
      const prevBtn = document.getElementById('manager-prev-page');
      const nextBtn = document.getElementById('manager-next-page');
      if (prevBtn) prevBtn.disabled = currentManagerPage <= 1;
      if (nextBtn) nextBtn.disabled = currentManagerPage >= totalPages;

      const pageNums = managerPagination.querySelectorAll('.page-num');
      pageNums.forEach((btn) => {
        const page = parseInt(btn.getAttribute('data-page'), 10);
        btn.classList.toggle('active', page === currentManagerPage);
        btn.style.display = page <= totalPages ? 'flex' : 'none';
      });
    }
  }

  if (managerSearchInput) {
    managerSearchInput.addEventListener('input', () => {
      currentManagerPage = 1;
      renderPendingHazards();
    });
  }

  if (managerUrgencyFilter) {
    managerUrgencyFilter.addEventListener('change', () => {
      currentManagerPage = 1;
      renderPendingHazards();
    });
  }

  function openHazardDetail(item) {
    activeHazardTicket = item.ticket;

    if (detailTicketNumber) detailTicketNumber.textContent = item.ticket;
    if (detailLocation) detailLocation.textContent = item.location;
    if (detailCategory) detailCategory.textContent = item.category;
    if (detailDateMain) detailDateMain.textContent = item.date;
    if (detailDateSub) detailDateSub.textContent = item.time;

    // Display Attached Photo if present
    if (detailPhotoRow && detailPhotoImg) {
      if (item.photo) {
        detailPhotoImg.src = item.photo;
        detailPhotoRow.style.display = 'flex';
      } else {
        detailPhotoRow.style.display = 'none';
      }
    }

    if (managerListView && managerDetailView) {
      managerListView.classList.add('hidden');
      managerDetailView.classList.remove('hidden');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  function closeHazardDetail() {
    activeHazardTicket = null;
    if (managerListView && managerDetailView) {
      managerDetailView.classList.add('hidden');
      managerListView.classList.remove('hidden');
    }
  }

  if (btnHazardCancel) {
    btnHazardCancel.addEventListener('click', () => {
      closeHazardDetail();
    });
  }

  // Action: Mark Resolved
  if (btnHazardResolved) {
    btnHazardResolved.addEventListener('click', () => {
      const ticketToResolve = activeHazardTicket || (detailTicketNumber ? detailTicketNumber.textContent : null);
      if (!ticketToResolve) return;

      const allHazards = getStoredHazards();
      const targetIndex = allHazards.findIndex(h => h.ticket === ticketToResolve);

      if (targetIndex !== -1) {
        allHazards[targetIndex].status = 'Resolved';
        allHazards[targetIndex].resolvedDate = new Date().toLocaleDateString();
        saveStoredHazards(allHazards);

        // Record resolution in SQLite database
        if (window.API && window.API.hazards && typeof window.API.hazards.resolve === 'function') {
          window.API.hazards.resolve(ticketToResolve).catch(e => console.warn('Sync resolve to DB:', e.message));
        }

        addNotification(`Hazard Ticket ${ticketToResolve} Marked as Resolved`, { ticket: ticketToResolve });
        showToast(`Hazard "${ticketToResolve}" officially RESOLVED & archived!`, 'success');
      }

      if (window.location.pathname.includes('manager-hazard-detail.html')) {
        setTimeout(() => {
          window.location.href = 'manager-resolved.html';
        }, 700);
      } else {
        closeHazardDetail();
        renderPendingHazards();
      }
    });
  }

  if (managerPagination) {
    const prevBtn = document.getElementById('manager-prev-page');
    const nextBtn = document.getElementById('manager-next-page');
    const pageButtons = managerPagination.querySelectorAll('.page-num');

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (currentManagerPage > 1) {
          currentManagerPage--;
          renderPendingHazards();
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        currentManagerPage++;
        renderPendingHazards();
      });
    }

    pageButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const pageNum = parseInt(btn.getAttribute('data-page'), 10);
        if (!isNaN(pageNum)) {
          currentManagerPage = pageNum;
          renderPendingHazards();
        }
      });
    });
  }

  // Query parameter ticket viewer support
  const urlParams = new URLSearchParams(window.location.search);
  const ticketParam = urlParams.get('ticket');
  if (ticketParam) {
    const allHazards = getStoredHazards();
    const foundHazard = allHazards.find(h => h.ticket === ticketParam) || {
      ticket: ticketParam,
      location: 'Site X - Location',
      category: 'General Workplace Incident',
      date: '03-15-26',
      time: '10:00 AM',
      urgency: 'High',
      status: 'Pending'
    };
    openHazardDetail(foundHazard);
  } else if (managerHazardsList) {
    renderPendingHazards();
  }

  /* ============================================
     14. MANAGER RESOLVED HAZARDS
     ============================================ */
  const resolvedRowsList = document.getElementById('manager-resolved-rows-list');
  const resolvedSearchInput = document.getElementById('resolved-search-input');
  const resolvedLocInput = document.getElementById('resolved-location-input') || document.getElementById('resolved-location-filter');
  const resolvedDateFilter = document.getElementById('resolved-date-filter');
  const resolvedPagination = document.getElementById('manager-resolved-pagination');
  const btnExportResolvedCsv = document.getElementById('btn-export-resolved-csv');

  if (resolvedRowsList) {
    let currentResolvedPage = 1;
    const resolvedPerPage = 6;

    function renderResolvedHazards() {
      const allHazards = getStoredHazards();
      const query = (resolvedSearchInput?.value || '').toLowerCase().trim();
      const locQuery = (resolvedLocInput?.value || '').toLowerCase().trim();
      const dateVal = resolvedDateFilter?.value || '';

      const filteredList = allHazards.filter(item => {
        if (item.status !== 'Resolved') return false;
        const matchQ = !query || item.ticket.toLowerCase().includes(query) || item.category.toLowerCase().includes(query);
        const matchLoc = !locQuery || locQuery === 'all' || (item.location || '').toLowerCase().includes(locQuery);
        const matchDate = !dateVal || item.date.includes(dateVal);
        return matchQ && matchLoc && matchDate;
      });

      resolvedRowsList.innerHTML = '';
      const totalPages = Math.max(1, Math.ceil(filteredList.length / resolvedPerPage));
      if (currentResolvedPage > totalPages) currentResolvedPage = totalPages;

      const start = (currentResolvedPage - 1) * resolvedPerPage;
      const pageItems = filteredList.slice(start, start + resolvedPerPage);

      if (pageItems.length === 0) {
        resolvedRowsList.innerHTML = `
          <div style="text-align: center; padding: 40px; font-weight: 600; color: #555;">
            No matching resolved hazards found.
          </div>`;
      } else {
        pageItems.forEach((item, index) => {
          const isBlue = (index % 2 === 1);
          const rowClass = isBlue ? 'hazard-row-blue' : 'hazard-row-white';

          const row = document.createElement('div');
          row.className = `manager-hazard-row ${rowClass}`;
          row.innerHTML = `
            <div class="cell-ticket">
              <svg viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
              <span>${escapeHTML(item.ticket)}</span>
            </div>
            <div class="cell-location">
              <svg viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
              <span>${escapeHTML(item.location)}</span>
            </div>
            <div class="cell-category">${escapeHTML(item.category)}</div>
            <div class="cell-date">
              <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
              <div class="date-text-group">
                <span class="date-main">${escapeHTML(item.date)}</span>
                <span class="date-sub">${escapeHTML(item.time)}</span>
              </div>
            </div>
            <div class="cell-status-resolved">${escapeHTML(item.status)}</div>
            <div class="cell-action">
              <button type="button" class="btn-view-hazard" data-ticket="${escapeHTML(item.ticket)}">View</button>
            </div>
          `;

          row.querySelector('.btn-view-hazard').addEventListener('click', () => {
            window.location.href = `manager-hazard-detail.html?ticket=${encodeURIComponent(item.ticket)}`;
          });

          resolvedRowsList.appendChild(row);
        });
      }

      if (resolvedPagination) {
        const prev = document.getElementById('resolved-prev-page');
        const next = document.getElementById('resolved-next-page');
        if (prev) prev.disabled = currentResolvedPage <= 1;
        if (next) next.disabled = currentResolvedPage >= totalPages;

        const pageBtns = resolvedPagination.querySelectorAll('.page-num');
        pageBtns.forEach(btn => {
          const p = parseInt(btn.getAttribute('data-page'), 10);
          btn.classList.toggle('active', p === currentResolvedPage);
          btn.style.display = p <= totalPages ? 'flex' : 'none';
        });
      }
    }

    if (resolvedSearchInput) resolvedSearchInput.addEventListener('input', () => { currentResolvedPage = 1; renderResolvedHazards(); });
    if (resolvedLocInput) {
      resolvedLocInput.addEventListener('input', () => { currentResolvedPage = 1; renderResolvedHazards(); });
      resolvedLocInput.addEventListener('change', () => { currentResolvedPage = 1; renderResolvedHazards(); });
    }
    if (resolvedDateFilter) resolvedDateFilter.addEventListener('change', () => { currentResolvedPage = 1; renderResolvedHazards(); });

    if (resolvedPagination) {
      const prev = document.getElementById('resolved-prev-page');
      const next = document.getElementById('resolved-next-page');
      const pageBtns = resolvedPagination.querySelectorAll('.page-num');

      if (prev) {
        prev.addEventListener('click', () => {
          if (currentResolvedPage > 1) {
            currentResolvedPage--;
            renderResolvedHazards();
          }
        });
      }

      if (next) {
        next.addEventListener('click', () => {
          currentResolvedPage++;
          renderResolvedHazards();
        });
      }

      pageBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          const p = parseInt(btn.getAttribute('data-page'), 10);
          if (!isNaN(p)) {
            currentResolvedPage = p;
            renderResolvedHazards();
          }
        });
      });
    }

    // Wire CSV Export on manager-resolved.html
    if (btnExportResolvedCsv) {
      btnExportResolvedCsv.addEventListener('click', () => {
        const resolvedHazards = getStoredHazards().filter(h => h.status === 'Resolved');
        exportToCSV('SiteSafety_Resolved_Hazards.csv', resolvedHazards, [
          { label: 'Ticket Number', key: 'ticket' },
          { label: 'Location', key: 'location' },
          { label: 'Category', key: 'category' },
          { label: 'Incident Date', key: 'date' },
          { label: 'Incident Time', key: 'time' },
          { label: 'Status', key: 'status' },
          { label: 'Incident Cause', key: 'cause' },
          { label: 'Reporter', key: (h) => h.personnel?.name || '' }
        ]);
      });
    }

    renderResolvedHazards();
  }

  // HTML Escape Helper
  function escapeHTML(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
});
