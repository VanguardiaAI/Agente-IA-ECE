// Funciones adicionales para el panel de administración

// Toggle password visibility
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const toggle = document.getElementById(inputId + 'Toggle');
    
    if (input.type === 'password') {
        input.type = 'text';
        toggle.classList.remove('bi-eye');
        toggle.classList.add('bi-eye-slash');
    } else {
        input.type = 'password';
        toggle.classList.remove('bi-eye-slash');
        toggle.classList.add('bi-eye');
    }
}

// Check password strength
function checkPasswordStrength() {
    const password = document.getElementById('newPassword').value;
    const strengthBar = document.getElementById('passwordStrengthBar');
    const progressBar = strengthBar?.querySelector('.progress-bar');
    
    if (!progressBar) return;
    
    let strength = 0;
    let color = 'bg-danger';
    
    // Length check
    if (password.length >= 8) strength += 25;
    if (password.length >= 12) strength += 10;
    
    // Contains lowercase
    if (/[a-z]/.test(password)) strength += 20;
    
    // Contains uppercase
    if (/[A-Z]/.test(password)) strength += 20;
    
    // Contains numbers
    if (/[0-9]/.test(password)) strength += 20;
    
    // Contains special characters
    if (/[^A-Za-z0-9]/.test(password)) strength += 15;
    
    // Set color based on strength
    if (strength < 40) {
        color = 'bg-danger';
    } else if (strength < 70) {
        color = 'bg-warning';
    } else {
        color = 'bg-success';
    }
    
    // Update progress bar
    progressBar.className = 'progress-bar ' + color;
    progressBar.style.width = strength + '%';
    
    if (password.length > 0) {
        strengthBar.style.display = 'block';
    } else {
        strengthBar.style.display = 'none';
    }
}

// Check if passwords match
function checkPasswordMatch() {
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const feedback = document.getElementById('confirmPasswordFeedback');
    
    if (confirmPassword.length === 0) {
        feedback.textContent = 'Repite la nueva contraseña';
        feedback.className = 'text-muted';
    } else if (newPassword === confirmPassword) {
        feedback.textContent = '✅ Las contraseñas coinciden';
        feedback.className = 'text-success';
    } else {
        feedback.textContent = '❌ Las contraseñas no coinciden';
        feedback.className = 'text-danger';
    }
}

// Hacer las funciones disponibles globalmente
window.togglePasswordVisibility = togglePasswordVisibility;
window.checkPasswordStrength = checkPasswordStrength;
window.checkPasswordMatch = checkPasswordMatch;