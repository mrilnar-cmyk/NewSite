/**
 * Основной JavaScript файл
 * Общие функции и утилиты
 */

// CSRF Token для AJAX запросов


function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Настройка fetch для CSRF
function fetchWithCSRF(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CSRF_TOKEN || getCookie('csrftoken'),
        },
    };

    return fetch(url, { ...defaultOptions, ...options });
}

// ===================================
// УТИЛИТЫ
// ===================================

/**
 * Форматирование числа с заданной точностью
 */
function formatNumber(value, decimals = 4) {
    if (value === null || value === undefined || isNaN(value)) {
        return '—';
    }

    const num = parseFloat(value);

    // Для очень больших или очень маленьких чисел используем экспоненциальную запись
    if (Math.abs(num) >= 1e6 || (Math.abs(num) < 1e-4 && num !== 0)) {
        return num.toExponential(decimals);
    }

    return num.toFixed(decimals).replace(/\.?0+$/, '');
}

/**
 * Debounce функция для оптимизации частых вызовов
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Показать уведомление
 */
function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    // Автоматическое скрытие через 5 секунд
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

/**
 * Показать спиннер загрузки
 */
function showLoading(element) {
    const spinner = document.createElement('div');
    spinner.className = 'spinner-border spinner-border-sm ms-2';
    spinner.setAttribute('role', 'status');
    element.appendChild(spinner);
    element.disabled = true;
    return spinner;
}

/**
 * Скрыть спиннер загрузки
 */
function hideLoading(element, spinner) {
    if (spinner && spinner.parentNode) {
        spinner.remove();
    }
    element.disabled = false;
}

// ===================================
// ИНИЦИАЛИЗАЦИЯ
// ===================================

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация всплывающих подсказок Bootstrap
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipTriggerList.forEach(el => new bootstrap.Tooltip(el));

    // Автофокус на первом поле ввода в формах
    const firstInput = document.querySelector('form input:not([type="hidden"]):not([readonly])');
    if (firstInput) {
        firstInput.focus();
    }

    console.log('Formula initialized');
});