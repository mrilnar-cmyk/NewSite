/**
 * Страница вычисления конкретной формулы
 */

document.addEventListener('DOMContentLoaded', function() {
    const calculateBtn = document.getElementById('calculate-btn');
    const resetBtn = document.getElementById('reset-btn');
    const formulaId = document.getElementById('formula-id');
    const resultCard = document.getElementById('result-card');
    const errorCard = document.getElementById('error-card');
    const mainResult = document.getElementById('main-result');
    const resultValue = document.getElementById('result-value');
    const errorMessage = document.getElementById('error-message');
    const intermediateResults = document.getElementById('intermediate-results');
    const intermediateTbody = document.getElementById('intermediate-tbody');

    if (!calculateBtn) return;

    // ===================================
    // ВЫЧИСЛЕНИЕ
    // ===================================

    calculateBtn.addEventListener('click', performCalculation);

    // Вычисление по Enter в любом поле
    document.querySelectorAll('.variable-input').forEach(input => {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                performCalculation();
            }
        });
    });

    async function performCalculation() {
        // Собираем значения
        const values = {};
        let hasError = false;

        document.querySelectorAll('.variable-input').forEach(input => {
            const symbol = input.dataset.symbol;
            const value = input.value.trim();

            if (value === '') {
                input.classList.add('is-invalid');
                hasError = true;
            } else {
                input.classList.remove('is-invalid');
                values[symbol] = value;
            }
        });

        if (hasError) {
            showError('Заполните все поля');
            return;
        }

        // Показываем загрузку
        const spinner = showLoading(calculateBtn);
        calculateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Вычисление...';

        try {
            const response = await fetchWithCSRF('/formulas/api/calculate/', {
                method: 'POST',
                body: JSON.stringify({
                    formula_id: formulaId.value,
                    values: values,
                }),
            });

            const data = await response.json();

            if (data.success) {
                showResult(data);
            } else {
                showError(data.error);
            }
        } catch (error) {
            showError('Ошибка соединения с сервером');
            console.error('Calculation error:', error);
        } finally {
            hideLoading(calculateBtn, spinner);
            calculateBtn.innerHTML = '<i class="bi bi-play-fill"></i> Вычислить';
        }
    }

    /**
     * Показать результат
     */
    function showResult(data) {
        resultCard.style.display = 'block';
        resultCard.classList.add('fade-in');
        errorCard.style.display = 'none';

        // Главный результат
        if (data.main_result) {
            const value = formatNumber(data.main_result.value);
            mainResult.textContent = value;

            if (resultValue) {
                resultValue.textContent = value;
            }
        }

        // Промежуточные результаты
        if (data.results && Object.keys(data.results).length > 1) {
            intermediateResults.style.display = 'block';

            let html = '';
            for (const [symbol, result] of Object.entries(data.results)) {
                const statusClass = result.success ? 'text-success' : 'text-danger';
                const statusIcon = result.success ? 'bi-check-circle' : 'bi-x-circle';
                const value = result.success ? formatNumber(result.value) : result.error;

                html += `
                    <tr>
                        <td><code class="fs-5">${symbol}</code></td>
                        <td><code class="text-muted">${result.expression || '—'}</code></td>
                        <td class="${statusClass}">
                            <i class="bi ${statusIcon}"></i>
                            <strong>${value}</strong>
                        </td>
                    </tr>
                `;
            }

            intermediateTbody.innerHTML = html;
        } else {
            intermediateResults.style.display = 'none';
        }

        // Прокрутка к результату
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    /**
     * Показать ошибку
     */
    function showError(message) {
        resultCard.style.display = 'none';
        errorCard.style.display = 'block';
        errorCard.classList.add('fade-in');
        errorMessage.textContent = message;
        intermediateResults.style.display = 'none';
    }

    // ===================================
    // СБРОС
    // ===================================

    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            // Очищаем поля ввода
            document.querySelectorAll('.variable-input').forEach(input => {
                input.value = '';
                input.classList.remove('is-invalid');
            });

            // Скрываем результаты
            resultCard.style.display = 'none';
            errorCard.style.display = 'none';
            intermediateResults.style.display = 'none';
        });
    }

    // ===================================
    // АВТОЗАПОЛНЕНИЕ ИЗ ДРУГИХ ФОРМУЛ
    // ===================================

    // Проверяем, есть ли значения в URL (для передачи между страницами)
    const urlParams = new URLSearchParams(window.location.search);

    document.querySelectorAll('.variable-input').forEach(input => {
        const symbol = input.dataset.symbol;
        const paramValue = urlParams.get(symbol);

        if (paramValue) {
            input.value = paramValue;
        }
    });
});