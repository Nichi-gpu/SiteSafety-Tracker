document.addEventListener('DOMContentLoaded', () => {
  const loginForm  = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');

  // Swap icon to match the role chosen on the landing page
  const selectedRole = localStorage.getItem('selectedRole') || 'manager';
  const roleIcon = document.getElementById('role-icon');
  if (roleIcon) {
    const origSrc = roleIcon.getAttribute('src') || '';
    const prefix = origSrc.startsWith('assets/') ? 'assets/' : '';
    const iconFile = selectedRole === 'staff' ? 'staff-blue.png' : 'manager_clean_icon.png';
    roleIcon.src = prefix + iconFile;
    roleIcon.alt = selectedRole === 'staff' ? 'Staff role icon' : 'Manager role icon';

    // Safety fallback: if relative path fails, try alternate path
    roleIcon.onerror = function() {
      if (!this.src.includes('assets/')) {
        this.src = 'assets/' + iconFile;
      } else {
        this.src = iconFile;
      }
    };
  }

  // Create or get notification message container
  function getMessageBanner(form) {
    let banner = form.querySelector('.auth-message-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.className = 'auth-message-banner';
      banner.style.cssText = 'padding: 10px 14px; border-radius: 8px; font-size: 13px; font-weight: 500; margin-bottom: 15px; text-align: center; display: none;';
      form.insertBefore(banner, form.firstChild);
    }
    return banner;
  }

  function showMessage(form, msg, type = 'error') {
    const banner = getMessageBanner(form);
    banner.style.display = 'block';
    if (type === 'error') {
      banner.style.background = '#fef2f2';
      banner.style.color = '#b91c1c';
      banner.style.border = '1px solid #f87171';
    } else {
      banner.style.background = '#ecfdf5';
      banner.style.color = '#047857';
      banner.style.border = '1px solid #34d399';
    }
    banner.textContent = msg;
  }

  function hideMessage(form) {
    const banner = form.querySelector('.auth-message-banner');
    if (banner) banner.style.display = 'none';
  }

  /* ========== LOGIN ========== */
  if (loginForm) {
    // Pre-fill remembered email or username
    const saved = localStorage.getItem('rememberedEmail');
    if (saved) {
      const emailInput = document.getElementById('login-email');
      if (emailInput) emailInput.value = saved;
      const remBox = document.getElementById('remember-me');
      if (remBox) remBox.checked = true;
    }

    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearErrors();
      hideMessage(loginForm);

      const identifier = val('login-email');
      const password = (document.getElementById('login-password') || {}).value || '';
      const remember = (document.getElementById('remember-me') || {}).checked || false;
      const loginBtn = document.getElementById('login-btn');

      if (!identifier) return showError('login-email', 'Email or Username is required');
      if (!password) return showError('login-password', 'Password is required');
      if (password.length < 6) return showError('login-password', 'Min 6 characters');

      // Remember me
      if (remember) localStorage.setItem('rememberedEmail', identifier);
      else localStorage.removeItem('rememberedEmail');

      const origBtnText = loginBtn ? loginBtn.innerText : 'LOGIN';
      if (loginBtn) {
        loginBtn.disabled = true;
        loginBtn.innerText = 'LOGGING IN...';
      }

      try {
        if (typeof API === 'undefined' || !API.auth) {
          throw new Error('API client script not loaded. Please refresh the page.');
        }

        const res = await API.auth.login(identifier, password);
        const user = res.user || {};

        // Determine effective role: prioritize user's explicitly chosen role from landing page
        const chosenRole = (localStorage.getItem('selectedRole') || '').toLowerCase();
        let effectiveRole = 'staff';

        if (chosenRole === 'staff') {
          // Explicitly chose Staff: always route to Staff portal
          effectiveRole = 'staff';
        } else if (chosenRole === 'manager') {
          // Explicitly chose Manager: verify user has manager privileges
          if (user.role && user.role !== 'manager') {
            effectiveRole = 'staff';
            showMessage(loginForm, 'Notice: Your account has Staff privileges only. Directing to Staff portal...', 'info');
          } else {
            effectiveRole = 'manager';
          }
        } else {
          // Direct login fallback without landing selection
          effectiveRole = user.role || 'staff';
        }

        // Persist session info in localStorage
        localStorage.setItem('isLoggedIn', 'true');
        localStorage.setItem('userEmail', user.email || identifier);
        localStorage.setItem('username', user.username || identifier);
        localStorage.setItem('userRole', user.role || effectiveRole);
        localStorage.setItem('userCompany', user.company || '');
        localStorage.setItem('signupTime', user.signup_time || '');
        localStorage.setItem('lastLoginTime', user.last_login_time || '');
        localStorage.setItem('selectedRole', effectiveRole);

        showMessage(loginForm, `Login successful! Welcome back, ${user.username || user.email}!`, 'success');

        // Redirect based on effective role
        setTimeout(() => {
          if (effectiveRole === 'staff') {
            window.location.href = 'home.html';
          } else {
            window.location.href = 'manager-home.html';
          }
        }, 600);

      } catch (err) {
        console.error('Login error:', err);
        showMessage(loginForm, err.message || 'Login failed. Please check your credentials.', 'error');
        if (loginBtn) {
          loginBtn.disabled = false;
          loginBtn.innerText = origBtnText;
        }
      }
    });

    // ── Forgot Password Modal & Verification Code Workflow ──
    const forgotLink = document.getElementById('forgot-password');
    const forgotModal = document.getElementById('forgot-modal');
    const forgotCloseBtn = document.getElementById('forgot-close-btn');
    const forgotCancelBtn = document.getElementById('forgot-cancel-btn');
    const forgotBackBtn = document.getElementById('forgot-back-btn');
    const forgotFinishBtn = document.getElementById('forgot-finish-btn');
    const forgotStep1 = document.getElementById('forgot-step1-form');
    const forgotStep2 = document.getElementById('forgot-step2-form');
    const forgotStep3 = document.getElementById('forgot-step3-success');
    const forgotAlert = document.getElementById('forgot-alert-banner');
    const forgotEmailInput = document.getElementById('forgot-email');
    const forgotCodeInput = document.getElementById('forgot-code');
    const forgotTargetEmail = document.getElementById('forgot-target-email');

    let activeResetEmail = '';

    function showForgotAlert(msg, type = 'error') {
      if (!forgotAlert) return;
      forgotAlert.className = `modal-alert-banner ${type}`;
      forgotAlert.textContent = msg;
      forgotAlert.style.display = 'block';
    }

    function hideForgotAlert() {
      if (!forgotAlert) return;
      forgotAlert.style.display = 'none';
      forgotAlert.textContent = '';
    }

    function openForgotModal() {
      if (!forgotModal) return;
      hideForgotAlert();
      activeResetEmail = '';
      if (forgotStep1) forgotStep1.style.display = 'block';
      if (forgotStep2) forgotStep2.style.display = 'none';
      if (forgotStep3) forgotStep3.style.display = 'none';

      // Pre-populate email if user typed one in login box
      const existingEmail = (document.getElementById('login-email')?.value || '').trim();
      if (existingEmail && existingEmail.includes('@') && forgotEmailInput) {
        forgotEmailInput.value = existingEmail;
      }
      forgotModal.style.display = 'flex';
      if (forgotEmailInput) setTimeout(() => forgotEmailInput.focus(), 80);
    }

    function closeForgotModal() {
      if (forgotModal) forgotModal.style.display = 'none';
      hideForgotAlert();
    }

    if (forgotLink) {
      forgotLink.addEventListener('click', (e) => {
        e.preventDefault();
        openForgotModal();
      });
    }

    if (forgotCloseBtn) forgotCloseBtn.addEventListener('click', closeForgotModal);
    if (forgotCancelBtn) forgotCancelBtn.addEventListener('click', closeForgotModal);

    // Close on backdrop click
    if (forgotModal) {
      forgotModal.addEventListener('click', (e) => {
        if (e.target === forgotModal) closeForgotModal();
      });
    }

    // Step 1: Send verification code
    if (forgotStep1) {
      forgotStep1.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideForgotAlert();

        const email = (forgotEmailInput?.value || '').trim().toLowerCase();
        if (!email) {
          showForgotAlert('Please enter your email address.', 'error');
          return;
        }

        const sendBtn = document.getElementById('forgot-send-btn');
        const origBtnText = sendBtn ? sendBtn.innerHTML : 'Send Code';
        if (sendBtn) {
          sendBtn.disabled = true;
          sendBtn.innerHTML = '<span>Sending Code...</span>';
        }

        try {
          let data;
          if (typeof API !== 'undefined' && API.auth && API.auth.forgotPassword) {
            data = await API.auth.forgotPassword(email);
          } else {
            const res = await fetch('/api/auth/forgot-password', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ email })
            });
            data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to send verification code.');
          }

          activeResetEmail = data.email || email;
          if (forgotTargetEmail) forgotTargetEmail.textContent = data.masked_email || activeResetEmail;

          // Transition to Step 2
          forgotStep1.style.display = 'none';
          forgotStep2.style.display = 'block';

          if (data.dev_code) {
            showForgotAlert(`Test Code (Dev Mode): ${data.dev_code}`, 'info');
          } else {
            showForgotAlert('Code sent! Please check your Inbox and Spam/Junk folder.', 'info');
          }

          if (forgotCodeInput) {
            forgotCodeInput.value = '';
            setTimeout(() => forgotCodeInput.focus(), 100);
          }
        } catch (err) {
          showForgotAlert(err.message || 'Cannot connect to server. Please ensure the backend is running.', 'error');
        } finally {
          if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.innerHTML = origBtnText;
          }
        }
      });
    }

    // Step 2 Back Button
    if (forgotBackBtn) {
      forgotBackBtn.addEventListener('click', () => {
        hideForgotAlert();
        if (forgotStep2) forgotStep2.style.display = 'none';
        if (forgotStep1) forgotStep1.style.display = 'block';
        if (forgotEmailInput) forgotEmailInput.focus();
      });
    }

    // Step 2: Verify code and update password
    if (forgotStep2) {
      forgotStep2.addEventListener('submit', async (e) => {
        e.preventDefault();
        hideForgotAlert();

        const code = (forgotCodeInput?.value || '').trim();
        const newPass = (document.getElementById('forgot-new-pass')?.value || '').trim();
        const confirmPass = (document.getElementById('forgot-confirm-pass')?.value || '').trim();

        if (!code || code.length !== 6) {
          showForgotAlert('Please enter the valid 6-digit verification code.', 'error');
          return;
        }

        if (newPass.length < 6) {
          showForgotAlert('Password must be at least 6 characters.', 'error');
          return;
        }

        if (!/\d/.test(newPass)) {
          showForgotAlert('Password must include at least one number (0-9).', 'error');
          return;
        }

        if (!/[^a-zA-Z0-9]/.test(newPass)) {
          showForgotAlert('Password must include at least one special character (!@#$%^&*).', 'error');
          return;
        }

        if (newPass !== confirmPass) {
          showForgotAlert('Passwords do not match. Please re-enter.', 'error');
          return;
        }

        const resetBtn = document.getElementById('forgot-reset-btn');
        const origText = resetBtn ? resetBtn.innerHTML : 'Update Password';
        if (resetBtn) {
          resetBtn.disabled = true;
          resetBtn.innerHTML = '<span>Updating...</span>';
        }

        try {
          let data;
          if (typeof API !== 'undefined' && API.auth && API.auth.resetPassword) {
            data = await API.auth.resetPassword(activeResetEmail, code, newPass);
          } else {
            const res = await fetch('/api/auth/reset-password', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                email: activeResetEmail,
                code,
                new_password: newPass
              })
            });
            data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Failed to reset password. Check code or request a new one.');
          }

          // Transition to Step 3: Success
          forgotStep2.style.display = 'none';
          forgotStep3.style.display = 'block';
        } catch (err) {
          showForgotAlert(err.message || 'Network error. Failed to communicate with server.', 'error');
        } finally {
          if (resetBtn) {
            resetBtn.disabled = false;
            resetBtn.innerHTML = origText;
          }
        }
      });
    }

    // Step 3 Finish Button
    if (forgotFinishBtn) {
      forgotFinishBtn.addEventListener('click', () => {
        closeForgotModal();
        const loginEmail = document.getElementById('login-email');
        const loginPassword = document.getElementById('login-password');
        if (loginEmail && activeResetEmail) loginEmail.value = activeResetEmail;
        if (loginPassword) {
          loginPassword.value = '';
          loginPassword.focus();
        }
        showMessage(loginForm, 'Password reset successful! Please enter your new password to log in.', 'success');
      });
    }
  }

  /* ========== SIGN UP ========== */
  if (signupForm) {
    signupForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearErrors();
      hideMessage(signupForm);

      const company  = val('signup-company');
      const usernameInput = document.getElementById('signup-username');
      const username = usernameInput ? usernameInput.value.trim() : '';
      const email    = val('signup-email');
      const password = (document.getElementById('signup-password') || {}).value || '';
      const verified = (document.getElementById('verify-checkbox') || {}).checked || false;
      const signupBtn = document.getElementById('signup-btn');

      if (!company) return showError('signup-company', 'Company is required');
      if (usernameInput && !username) return showError('signup-username', 'Username is required');
      if (usernameInput && username.length < 3) return showError('signup-username', 'Min 3 characters');
      if (!email) return showError('signup-email', 'Email is required');
      if (!isValidEmail(email)) return showError('signup-email', 'Enter a valid email');
      if (!password) return showError('signup-password', 'Password is required');
      if (password.length < 6) return showError('signup-password', 'Min 6 characters');
      if (!/\d/.test(password)) return showError('signup-password', 'Must contain at least 1 number (0-9)');
      if (!/[^a-zA-Z0-9]/.test(password)) return showError('signup-password', 'Must contain at least 1 special char (!@#$...)');
      if (!verified) {
        alert('Please check the "Verify account credentials" box to continue.');
        return;
      }

      const origBtnText = signupBtn ? signupBtn.innerText : 'SIGN UP';
      if (signupBtn) {
        signupBtn.disabled = true;
        signupBtn.innerText = 'CREATING ACCOUNT...';
      }

      try {
        if (typeof API === 'undefined' || !API.auth) {
          throw new Error('API client script not loaded. Please refresh the page.');
        }

        const res = await API.auth.signup({
          company,
          username: username || email.split('@')[0],
          email,
          password,
          role: selectedRole
        });

        showMessage(signupForm, 'Account created successfully! Redirecting to login...', 'success');

        // Pre-fill email on login page
        localStorage.setItem('rememberedEmail', email);

        setTimeout(() => {
          window.location.href = 'login.html';
        }, 1200);

      } catch (err) {
        console.error('Signup error:', err);
        showMessage(signupForm, err.message || 'Signup failed. Please try again.', 'error');
        if (signupBtn) {
          signupBtn.disabled = false;
          signupBtn.innerText = origBtnText;
        }
      }
    });
  }

  /* ========== UTILITIES ========== */
  function val(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : '';
  }

  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function showError(id, msg) {
    const input = document.getElementById(id);
    if (!input) return;
    input.classList.add('input-error');
    input.placeholder = msg;
    input.value = '';
    input.focus();

    input.addEventListener('input', function handler() {
      input.classList.remove('input-error');
      input.removeEventListener('input', handler);
    });
  }

  function clearErrors() {
    document.querySelectorAll('.input-error').forEach((el) => {
      el.classList.remove('input-error');
    });
  }

  // Focus highlight for all auth inputs
  document.querySelectorAll('.auth-form input[type]').forEach((input) => {
    input.addEventListener('focus', () => {
      if (!input.classList.contains('input-error')) {
        input.style.borderColor = '#0d4aa5';
      }
    });
    input.addEventListener('blur', () => {
      if (!input.classList.contains('input-error')) {
        input.style.borderColor = '';
      }
    });
  });
});
