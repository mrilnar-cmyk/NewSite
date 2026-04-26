/**
 * Редактор формул
 * Обработка ввода, панель символов, предпросмотр
 */

document.addEventListener('DOMContentLoaded', function() {
    const expressionInput = document.getElementById('expression-input');
    const formulaPreview = document.getElementById('formula-preview');
    const detectedVariables = document.getElementById('detected-variables');
    const formulaToolbar = document.getElementById('formula-toolbar');
    const isInputCheckbox = document.getElementById('id_is_input');
    const expressionSection = document.getElementById('expression-section');
    const defaultValueSection = document.getElementById('default-value-section');

    if (!expressionInput) return;

    // ===================================
    // ПАНЕЛЬ СИМВОЛОВ
    // ===================================

    if (formulaToolbar) {
        formulaToolbar.addEventListener('click', function(e) {
            const btn = e.target.closest('button[data-insert]');
            if (!btn) return;

            e.preventDefault();
            const insertText = btn.dataset.insert;
            insertAtCursor(expressionInput, insertText);
            updatePreview();
        });
    }

    /**
     * Вставка текста в позицию курсора
     */
    function insertAtCursor(input, text) {
        const start = input.selectionStart;
        const end = input.selectionEnd;
        const value = input.value;

        // Определяем позицию курсора после вставки
        let cursorPos = start + text.length;

        // Для функций со скобками ставим курсор внутрь
        if (text.endsWith('()')) {
            cursorPos = start + text.length - 1;
        } else if (text === '()') {
            cursorPos = start + 1;
        } else if (text === 'if(,,)') {
            cursorPos = start + 3;
        }

        input.value = value.substring(0, start) + text + value.substring(end);
        input.focus();
        input.setSelectionRange(cursorPos, cursorPos);
    }

    // ===================================
    // ПРЕДПРОСМОТР ФОРМУЛЫ
    // ===================================

    if (expressionInput) {
        expressionInput.addEventListener('input', debounce(updatePreview, 300));
        // Начальное обновление
        updatePreview();
    }

   function updatePreview() {
        const expression = expressionInput.value.trim();
        const symbolField = document.getElementById('id_symbol');
        const symbol = symbolField ? symbolField.value.trim() || '?' : '?';

        if (!expression) {
            formulaPreview.innerHTML = '<span class="text-muted fst-italic">Введите формулу...</span>';
            detectedVariables.innerHTML = '<span class="text-muted fst-italic">Переменные появятся автоматически</span>';
            return;
        }

        fetch('/formulas/api/latex-preview/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN,
            },
            body: JSON.stringify({
                expression: expression,
                symbol: symbol
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.latex) {
                formulaPreview.innerHTML = data.latex;
                if (typeof renderMathInElement !== 'undefined') {
                    renderMathInElement(formulaPreview, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '\\(', right: '\\)', display: false}
                        ],
                        throwOnError: false
                    });
                }
            } else {
                formulaPreview.innerHTML = `<code class="fs-4 text-danger">${symbol} = [ошибка разбора]</code>`;
            }
        })
        .catch(err => {
            console.error('LaTeX preview error:', err);
            formulaPreview.innerHTML = `<code class="fs-4">${symbol} = ${prettifyExpression(expression)}</code>`;
        });

        fetchVariables(expression);
    }

    /**
     * Преобразование выражения в красивый вид
     */
    function prettifyExpression(expr) {
        let pretty = expr;

        // Заменяем операторы
        pretty = pretty.replace(/\*/g, ' × ');
        pretty = pretty.replace(/\//g, ' ÷ ');
        pretty = pretty.replace(/\^(\d+)/g, '<sup>$1</sup>');
        pretty = pretty.replace(/\^(\([^)]+\))/g, '<sup>$1</sup>');
        pretty = pretty.replace(/\*\*(\d+)/g, '<sup>$1</sup>');

        // Заменяем функции
        pretty = pretty.replace(/sqrt\(/g, '√(');
        pretty = pretty.replace(/cbrt\(/g, '∛(');

        // Заменяем константы
        pretty = pretty.replace(/\bpi\b/gi, 'π');

        // Заменяем греческие буквы
        const greekLetters = {
            'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ',
            'epsilon': 'ε', 'zeta': 'ζ', 'eta': 'η', 'theta': 'θ',
            'lambda': 'λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ',
            'rho': 'ρ', 'sigma': 'σ', 'tau': 'τ', 'phi': 'φ',
            'chi': 'χ', 'psi': 'ψ', 'omega': 'ω'
        };

        for (const [latin, greek] of Object.entries(greekLetters)) {
            const regex = new RegExp(`\\b${latin}\\b`, 'gi');
            pretty = pretty.replace(regex, greek);
        }

        return pretty;
    }

    /**
     * Получение переменных через API
     */
    async function fetchVariables(expression) {
        try {
            const response = await fetchWithCSRF('/formulas/api/parse/', {
                method: 'POST',
                body: JSON.stringify({ expression }),
            });

            const data = await response.json();

            if (data.success) {
                displayVariables(data.variables);
            } else {
                detectedVariables.innerHTML = `<span class="text-danger"><i class="bi bi-exclamation-triangle"></i> ${data.error}</span>`;
            }
        } catch (error) {
            console.error('Error fetching variables:', error);
        }
    }

    /**
     * Отображение обнаруженных переменных
     */
    function displayVariables(variables) {
        if (!variables || variables.length === 0) {
            detectedVariables.innerHTML = '<span class="text-muted fst-italic">Нет переменных (только константы)</span>';
            return;
        }

        let html = '<div class="d-flex flex-wrap gap-2">';

        for (const v of variables) {
            const badgeClass = v.is_formula ? 'bg-success' : 'bg-primary';
            const icon = v.is_formula ? '<i class="bi bi-link"></i>' : '<i class="bi bi-input-cursor-text"></i>';
            const title = v.is_formula ? 'Результат другой формулы' : 'Входной параметр';

            html += `<span class="badge ${badgeClass}" title="${title}">${icon} ${v.symbol}</span>`;
        }

        html += '</div>';

        // Добавляем пояснение
        const inputVars = variables.filter(v => !v.is_formula);
        const formulaVars = variables.filter(v => v.is_formula);

        if (inputVars.length > 0 || formulaVars.length > 0) {
            html += '<div class="mt-2 small text-muted">';
            if (inputVars.length > 0) {
                html += `<span class="me-3"><i class="bi bi-input-cursor-text text-primary"></i> Ввод: ${inputVars.length}</span>`;
            }
            if (formulaVars.length > 0) {
                html += `<span><i class="bi bi-link text-success"></i> Из формул: ${formulaVars.length}</span>`;
            }
            html += '</div>';
        }

        detectedVariables.innerHTML = html;
    }

    
    // ПЕРЕКЛЮЧЕНИЕ ТИПА ФОРМУЛЫ
    
    if (isInputCheckbox) {
        isInputCheckbox.addEventListener('change', toggleFormulaType);
        // Начальное состояние
        toggleFormulaType();
    }

    function toggleFormulaType() {
        const isInput = isInputCheckbox.checked;

        if (expressionSection) {
            expressionSection.style.display = isInput ? 'none' : 'block';
        }

        if (defaultValueSection) {
            defaultValueSection.style.display = isInput ? 'block' : 'none';
        }
    }
});