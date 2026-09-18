document.addEventListener('DOMContentLoaded', () => {
  let selectedRole = localStorage.getItem('selectedRole') || 'manager';

  const managerCard = document.querySelector('.manager') || document.getElementById('wrapper-manager');
  const staffCard = document.querySelector('.staff') || document.getElementById('wrapper-staff');
  const submitBtn = document.querySelector('.submit-btn') || document.getElementById('submit-role');

  function setRole(role) {
    selectedRole = role;
    if (role === 'manager') {
      if (managerCard) managerCard.classList.add('selected');
      if (staffCard) staffCard.classList.remove('selected');
    } else {
      if (staffCard) staffCard.classList.add('selected');
      if (managerCard) managerCard.classList.remove('selected');
    }
  }

  // Set default initial selection
  setRole(selectedRole);

  if (managerCard) {
    managerCard.setAttribute('tabindex', '0');
    managerCard.setAttribute('role', 'button');
    managerCard.setAttribute('aria-label', 'Select Manager role');
    managerCard.addEventListener('click', () => setRole('manager'));
    managerCard.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setRole('manager');
      }
    });
  }

  if (staffCard) {
    staffCard.setAttribute('tabindex', '0');
    staffCard.setAttribute('role', 'button');
    staffCard.setAttribute('aria-label', 'Select Staff role');
    staffCard.addEventListener('click', () => setRole('staff'));
    staffCard.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setRole('staff');
      }
    });
  }

  if (submitBtn) {
    submitBtn.addEventListener('click', () => {
      if (!selectedRole) {
        alert('Please select a role to continue.');
        return;
      }
      localStorage.setItem('selectedRole', selectedRole);
      window.location.href = 'login.html';
    });
  }
});
