/**
 * Калькулятор - главная страница
 * Быстрый расчёт и поиск формул
 */

document.addEventListener('DOMContentLoaded', function() {
    const formulaSearch = document.getElementById('formula-search');
    const quickExpression = document.getElementById('quick-expression');
    const quickCalculateBtn = document.getElementById('quick-calculate-btn');
    const quickClearBtn = document.getElementById('quick-clear-btn');
    const quickResult = document.getElementById('quick-result');
    const quickError = document.getElementById('quick-error');
    const quickVariables = document.getElementById('quick-variables');

    // ===================================
    // ПОИСК ФОРМУЛ
    // ===================================

    if (formulaSearch) {
        formulaSearch.addEventListener('input', debounce(filterFormulas, 200));
    }

    function filterFormulas() {
        const searchText = formulaSearch.value.toLowerCase().trim();
        const formulaItems = document.querySelectorAll('.formula-item');

        formulaItems.forEach(item => {
            const symbol = (item.dataset.symbol || '').toLowerCase();
            const name = (item.dataset.name || '').toLowerCase();

            const matches = symbol.includes(searchText) || name.includes(searchText);

            // Показываем/скрываем элемент
            item.style.display = matches ? '' : 'none';
        });

        // Показываем категории, в которых есть видимые формулы
        document.querySelectorAll('.accordion-item').forEach(accordion => {
            const visibleItems = accordion.querySelectorAll('.formula-item[style=""]');
            const hasVisible = visibleItems.length > 0 || searchText === '';
            accordion.style.display = hasVisible ? '' : 'none';

            // Раскрываем аккордеон при поиске
            if (searchText && hasVisible) {
                const collapse = accordion.querySelector('.accordion-collapse');
                if (collapse) {
                    collapse.classList.add('show');
                }
            }
        });
    }

    // ===================================
    // БЫСТРЫЙ КАЛЬКУЛЯТОР
    // ===================================

    if (quickExpression) {
        quickExpression.addEventListener('input', debounce(updateQuickVariables, 300));
    }

    if (quickCalculateBtn) {
        quickCalculateBtn.addEventListener('click', performQuickCalculation);
    }

    if (quickClearBtn) {
        quickClearBtn.addEventListener('click', clearQuickCalculator);
    }

    /**
     * Обновление полей ввода переменных
     */
    async function updateQuickVariables() {
        const expression = quickExpression.value.trim();

        if (!expression) {
            quickVariables.innerHTML = '';
            return;
        }

        try {
            const response = await fetchWithCSRF('/formulas/api/parse/', {
                method: 'POST',
                body: JSON.stringify({ expression }),
            });

            const data = await response.json();

            if (data.success && data.variables.length > 0) {
                let html = '';
                for (const v of data.variables) {
                    if (!v.is_formula) {
                        html += `
                            <div class="col-md-4 col-6">
                                <div class="input-group input-group-sm">
                                    <span class="input-group-text"><code>${v.symbol}</code></span>
                                    <input type="number" step="any" class="form-control quick-var"
                                           data-symbol="${v.symbol}" placeholder="0">
                                </div>
                            </div>
                        `;
                    }
                }
                quickVariables.innerHTML = html;
            } else {
                quickVariables.innerHTML = '';
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    /**
     * Выполнение быстрого расчёта
     */
    async function performQuickCalculation() {
        const expression = quickExpression.value.trim();

        if (!expression) {
            showQuickError('Введите выражение');
            return;
        }

        // Собираем значения переменных
        const values = {};
        document.querySelectorAll('.quick-var').forEach(input => {
            const symbol = input.dataset.symbol;
            const value = input.value.trim();
            if (value !== '') {
                values[symbol] = value;
            }
        });

        // Показываем загрузку
        const spinner = showLoading(quickCalculateBtn);

        try {
            const response = await fetchWithCSRF('/formulas/api/quick-calculate/', {
                method: 'POST',
                body: JSON.stringify({ expression, values }),
            });

            const data = await response.json();

            if (data.success) {
                showQuickResult(data.value);
            } else {
                showQuickError(data.error);
            }
        } catch (error) {
            showQuickError('Ошибка соединения');
        } finally {
            hideLoading(quickCalculateBtn, spinner);
        }
    }

    function showQuickResult(value) {
        quickResult.style.display = 'block';
        quickError.style.display = 'none';
        document.getElementById('quick-result-value').textContent = formatNumber(value);
    }

    function showQuickError(message) {
        quickResult.style.display = 'none';
        quickError.style.display = 'block';
        document.getElementById('quick-error-message').textContent = message;
    }

    function clearQuickCalculator() {
        quickExpression.value = '';
        quickVariables.innerHTML = '';
        quickResult.style.display = 'none';
        quickError.style.display = 'none';
    }
});