// Recipe App JavaScript Enhancements
document.addEventListener('DOMContentLoaded', function () {
    // 1. Sidebar toggle en móvil
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.app-sidebar');
    const overlay = document.querySelector('.sidebar-overlay');

    if (sidebarToggle && sidebar && overlay) {
        sidebarToggle.addEventListener('click', function () {
            sidebar.classList.toggle('show');
            overlay.classList.toggle('show');
        });

        overlay.addEventListener('click', function () {
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
        });
    }

    // 2. Formulario de Cliente: Modalidad de 1 o 2 pagos al mes
    const monthlyFeeInput = document.getElementById('id_monthly_fee_usd');
    const paymentPartsSelect = document.getElementById('id_payment_parts');
    const firstPaymentInput = document.getElementById('id_first_payment_usd');
    const secondPaymentInput = document.getElementById('id_second_payment_usd');
    const firstPaymentAmountWrapper = document.getElementById('firstPaymentAmountWrapper');
    const secondPaymentCol = document.getElementById('secondPaymentCol');
    const firstPaymentTitle = document.getElementById('firstPaymentTitle');
    const labelFirstDay = document.getElementById('labelFirstDay');
    const btnSplitHalf = document.getElementById('btnSplitHalf');

    function togglePaymentPartsUI(recalculateSplit = false) {
        if (!paymentPartsSelect) return;
        const parts = parseInt(paymentPartsSelect.value, 10) || 1;
        const total = parseFloat(monthlyFeeInput ? monthlyFeeInput.value : 0) || 0;

        if (parts === 2) {
            if (firstPaymentAmountWrapper) firstPaymentAmountWrapper.style.display = 'block';
            if (secondPaymentCol) secondPaymentCol.style.display = 'block';
            if (firstPaymentTitle) firstPaymentTitle.innerHTML = '<i class="bi bi-calendar-check me-1"></i>1ra Parte del Pago Mensual';
            if (labelFirstDay) labelFirstDay.textContent = 'Día del 1er Cobro en el Mes (1 - 31) *';

            const currentFirst = parseFloat(firstPaymentInput ? firstPaymentInput.value : 0) || 0;
            if (recalculateSplit || currentFirst <= 0 || currentFirst >= total) {
                const half = (total / 2).toFixed(2);
                const rem = (total - parseFloat(half)).toFixed(2);
                if (firstPaymentInput) firstPaymentInput.value = half;
                if (secondPaymentInput) secondPaymentInput.value = rem;
            } else if (secondPaymentInput) {
                secondPaymentInput.value = Math.max(0, total - currentFirst).toFixed(2);
            }
        } else {
            if (firstPaymentAmountWrapper) firstPaymentAmountWrapper.style.display = 'none';
            if (secondPaymentCol) secondPaymentCol.style.display = 'none';
            if (firstPaymentTitle) firstPaymentTitle.innerHTML = '<i class="bi bi-calendar-check me-1"></i>Fecha de Cobro Mensual';
            if (labelFirstDay) labelFirstDay.textContent = 'Día de Cobro en el Mes (1 - 31) *';
            if (firstPaymentInput) firstPaymentInput.value = total.toFixed(2);
            if (secondPaymentInput) secondPaymentInput.value = '0.00';
        }
    }

    if (paymentPartsSelect) {
        paymentPartsSelect.addEventListener('change', function () {
            togglePaymentPartsUI(true);
        });
        togglePaymentPartsUI(false);
    }

    if (monthlyFeeInput) {
        monthlyFeeInput.addEventListener('input', function () {
            if (!paymentPartsSelect) return;
            const parts = parseInt(paymentPartsSelect.value, 10) || 1;
            const total = parseFloat(this.value) || 0;
            if (parts === 2) {
                const half = (total / 2).toFixed(2);
                const rem = (total - parseFloat(half)).toFixed(2);
                if (firstPaymentInput) firstPaymentInput.value = half;
                if (secondPaymentInput) secondPaymentInput.value = rem;
            } else {
                if (firstPaymentInput) firstPaymentInput.value = total.toFixed(2);
            }
        });
    }

    if (firstPaymentInput && secondPaymentInput && monthlyFeeInput) {
        firstPaymentInput.addEventListener('input', function () {
            const total = parseFloat(monthlyFeeInput.value) || 0;
            const first = parseFloat(this.value) || 0;
            const second = Math.max(0, total - first);
            secondPaymentInput.value = second.toFixed(2);
        });

        secondPaymentInput.addEventListener('input', function () {
            const total = parseFloat(monthlyFeeInput.value) || 0;
            const second = parseFloat(this.value) || 0;
            const first = Math.max(0, total - second);
            firstPaymentInput.value = first.toFixed(2);
        });
    }

    if (btnSplitHalf && monthlyFeeInput && firstPaymentInput && secondPaymentInput) {
        btnSplitHalf.addEventListener('click', function () {
            const total = parseFloat(monthlyFeeInput.value) || 0;
            const half = (total / 2).toFixed(2);
            const rem = (total - parseFloat(half)).toFixed(2);
            firstPaymentInput.value = half;
            secondPaymentInput.value = rem;
        });
    }

    // 3. Cálculo en tiempo real en formulario de Recibos
    const clientSelect = document.getElementById('id_client');
    const amountUsdInput = document.getElementById('id_amount_usd');
    const exchangeRateInput = document.getElementById('id_exchange_rate');
    const amountHnlInput = document.getElementById('id_amount_hnl');
    const conceptInput = document.getElementById('id_concept');
    const monthSelect = document.getElementById('id_billing_month');
    const yearInput = document.getElementById('id_billing_year');
    const clientBanner = document.getElementById('clientPaymentPlanBanner');
    const clientPlanText = document.getElementById('clientPlanText');
    const clientQuickAmounts = document.getElementById('clientQuickAmounts');

    function calculateReceiptHnl() {
        if (!amountUsdInput || !exchangeRateInput || !amountHnlInput) return;
        const usd = parseFloat(amountUsdInput.value) || 0;
        const rate = parseFloat(exchangeRateInput.value) || 0;
        const hnl = usd * rate;
        amountHnlInput.value = hnl.toFixed(2);

        const liveCalcPreview = document.getElementById('liveHnlPreview');
        if (liveCalcPreview) {
            liveCalcPreview.textContent = 'L ' + hnl.toLocaleString('es-HN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    }

    if (amountUsdInput && exchangeRateInput) {
        amountUsdInput.addEventListener('input', calculateReceiptHnl);
        exchangeRateInput.addEventListener('input', calculateReceiptHnl);
    }

    function applyReceiptSuggestion(amount, baseConcept, partLabel) {
        if (amountUsdInput) {
            amountUsdInput.value = parseFloat(amount).toFixed(2);
        }
        if (conceptInput) {
            let periodStr = '';
            if (monthSelect && yearInput) {
                const monthText = monthSelect.options[monthSelect.selectedIndex]?.text || '';
                periodStr = ` - ${monthText} ${yearInput.value}`;
            }
            const labelPart = partLabel ? ` (${partLabel})` : '';
            conceptInput.value = `${baseConcept}${labelPart}${periodStr}`;
        }
        calculateReceiptHnl();
    }

    function loadClientPaymentDetails(overwriteInputs = true) {
        if (!clientSelect || !clientSelect.value) {
            if (clientBanner) clientBanner.style.display = 'none';
            return;
        }
        const clientId = clientSelect.value;
        const m = monthSelect ? monthSelect.value : '';
        const y = yearInput ? yearInput.value : '';

        fetch(`/clients/api/${clientId}/?month=${m}&year=${y}`)
            .then(response => {
                if (!response.ok) throw new Error('Error al cargar datos del cliente');
                return response.json();
            })
            .then(data => {
                if (overwriteInputs) {
                    const usePartLabel = (data.payment_parts === 2 || data.paid_usd > 0) ? data.part_label : '';
                    applyReceiptSuggestion(data.suggested_usd, data.default_concept, usePartLabel);
                }

                if (clientBanner && clientPlanText && clientQuickAmounts) {
                    clientBanner.style.display = 'block';
                    let statusBadge = '';
                    if (data.remaining_usd <= 0 && data.monthly_fee_usd > 0) {
                        statusBadge = `<span class="badge bg-success ms-1">Mes Pagado Completo ($${data.paid_usd.toFixed(2)})</span>`;
                    } else if (data.paid_usd > 0) {
                        statusBadge = `<span class="badge bg-warning text-dark ms-1">Abonado: $${data.paid_usd.toFixed(2)} | Resta: $${data.remaining_usd.toFixed(2)}</span>`;
                    }

                    if (data.payment_parts === 2) {
                        clientPlanText.innerHTML = `
                            <strong>Modalidad en 2 Pagos</strong> (Total Mes: <strong>$${data.monthly_fee_usd.toFixed(2)} USD</strong>) &bull;
                            Día ${data.billing_day}: <strong>$${data.first_payment_usd.toFixed(2)}</strong> /
                            Día ${data.second_billing_day}: <strong>$${data.second_payment_usd.toFixed(2)}</strong>
                            ${statusBadge}
                        `;
                        clientQuickAmounts.innerHTML = '';

                        const btn1 = document.createElement('button');
                        btn1.type = 'button';
                        btn1.className = 'btn btn-outline-primary';
                        btn1.textContent = `1er Pago ($${data.first_payment_usd.toFixed(2)})`;
                        btn1.onclick = () => applyReceiptSuggestion(data.first_payment_usd, data.default_concept, '1er Pago');

                        const btn2 = document.createElement('button');
                        btn2.type = 'button';
                        btn2.className = 'btn btn-outline-primary';
                        const secondAmt = (data.paid_usd > 0 && data.remaining_usd > 0) ? data.remaining_usd : data.second_payment_usd;
                        btn2.textContent = `2do Pago ($${secondAmt.toFixed(2)})`;
                        btn2.onclick = () => applyReceiptSuggestion(secondAmt, data.default_concept, '2do Pago');

                        const btnFull = document.createElement('button');
                        btnFull.type = 'button';
                        btnFull.className = 'btn btn-outline-secondary';
                        btnFull.textContent = `Mes Completo ($${data.monthly_fee_usd.toFixed(2)})`;
                        btnFull.onclick = () => applyReceiptSuggestion(data.monthly_fee_usd, data.default_concept, '');

                        clientQuickAmounts.appendChild(btn1);
                        clientQuickAmounts.appendChild(btn2);
                        clientQuickAmounts.appendChild(btnFull);
                    } else {
                        clientPlanText.innerHTML = `
                            <strong>Cuota Mensual: $${data.monthly_fee_usd.toFixed(2)} USD</strong> (Día ${data.billing_day})
                            ${statusBadge}
                        `;
                        clientQuickAmounts.innerHTML = '';
                        if (data.paid_usd > 0 && data.remaining_usd > 0) {
                            const btnRem = document.createElement('button');
                            btnRem.type = 'button';
                            btnRem.className = 'btn btn-outline-primary';
                            btnRem.textContent = `Cobrar Saldo ($${data.remaining_usd.toFixed(2)})`;
                            btnRem.onclick = () => applyReceiptSuggestion(data.remaining_usd, data.default_concept, 'Saldo Restante');
                            clientQuickAmounts.appendChild(btnRem);
                        }
                        const btnHalf = document.createElement('button');
                        btnHalf.type = 'button';
                        btnHalf.className = 'btn btn-outline-secondary';
                        const halfAmt = (data.monthly_fee_usd / 2).toFixed(2);
                        btnHalf.textContent = `50% ($${halfAmt})`;
                        btnHalf.onclick = () => applyReceiptSuggestion(halfAmt, data.default_concept, 'Abono 50%');

                        const btnFull = document.createElement('button');
                        btnFull.type = 'button';
                        btnFull.className = 'btn btn-outline-primary';
                        btnFull.textContent = `100% ($${data.monthly_fee_usd.toFixed(2)})`;
                        btnFull.onclick = () => applyReceiptSuggestion(data.monthly_fee_usd, data.default_concept, '');

                        clientQuickAmounts.appendChild(btnHalf);
                        clientQuickAmounts.appendChild(btnFull);
                    }
                }
            })
            .catch(err => console.error('Error al obtener cliente:', err));
    }

    if (clientSelect) {
        clientSelect.addEventListener('change', function () {
            loadClientPaymentDetails(true);
        });
        if (monthSelect) {
            monthSelect.addEventListener('change', function () {
                loadClientPaymentDetails(true);
            });
        }
        if (yearInput) {
            yearInput.addEventListener('change', function () {
                loadClientPaymentDetails(true);
            });
        }
        if (clientSelect.value) {
            loadClientPaymentDetails(false);
        }
    }

    // 4. Cálculo en tiempo real en formulario de Gastos
    const expenseCurrency = document.getElementById('id_currency');
    const expenseAmount = document.getElementById('id_amount');
    const expenseRate = document.getElementById('id_exchange_rate');
    const expensePreviewHnl = document.getElementById('expensePreviewHnl');
    const expensePreviewUsd = document.getElementById('expensePreviewUsd');

    function updateExpenseCalculations() {
        if (!expenseAmount || !expenseRate) return;
        const amount = parseFloat(expenseAmount.value) || 0;
        const rate = parseFloat(expenseRate.value) || 0;
        const currency = expenseCurrency ? expenseCurrency.value : 'HNL';

        let hnl = 0;
        let usd = 0;

        if (currency === 'USD') {
            usd = amount;
            hnl = amount * rate;
        } else {
            hnl = amount;
            usd = rate > 0 ? (amount / rate) : 0;
        }

        if (expensePreviewHnl) {
            expensePreviewHnl.textContent = 'L ' + hnl.toLocaleString('es-HN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' HNL';
        }
        if (expensePreviewUsd) {
            expensePreviewUsd.textContent = '$ ' + usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' USD';
        }
    }

    if (expenseAmount && expenseRate) {
        expenseAmount.addEventListener('input', updateExpenseCalculations);
        expenseRate.addEventListener('input', updateExpenseCalculations);
        if (expenseCurrency) {
            expenseCurrency.addEventListener('change', updateExpenseCalculations);
        }
        updateExpenseCalculations();
    }
});
