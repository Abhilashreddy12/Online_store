// registration.js - Client-side validation for registration form

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const username = form.querySelector('input[name="username"]');
    const email = form.querySelector('input[name="email"]');
    const password1 = form.querySelector('input[name="password1"]');
    const password2 = form.querySelector('input[name="password2"]');
    const warningBox = document.createElement('ul');
    warningBox.id = 'registration-warnings';
    form.insertBefore(warningBox, form.firstChild);

    function showWarnings(warnings) {
        warningBox.innerHTML = '';
        warnings.forEach(w => {
            const li = document.createElement('li');
            li.textContent = w;
            warningBox.appendChild(li);
        });
        warningBox.style.display = warnings.length ? 'block' : 'none';
    }

    form.addEventListener('submit', function(e) {
        const warnings = [];
        // Username validation
        if (username.value.trim().length < 3) {
            warnings.push('Username must be at least 3 characters.');
        }
        // Email validation
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(email.value.trim())) {
            warnings.push('Please enter a valid email address.');
        }
        // Password validation
        if (password1.value.length < 8) {
            warnings.push('Password must be at least 8 characters.');
        }
        if (password1.value !== password2.value) {
            warnings.push('Passwords do not match.');
        }
        // Password strength (at least one number, one letter)
        if (!/(?=.*[A-Za-z])(?=.*\d)/.test(password1.value)) {
            warnings.push('Password must contain at least one letter and one number.');
        }
        if (warnings.length) {
            e.preventDefault();
            showWarnings(warnings);
        } else {
            showWarnings([]);
        }
    });
});
