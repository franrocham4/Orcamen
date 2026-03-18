/* dashboard.js - Chart initialization for Controle de Pagamento */

function initDashboardCharts(porMes, contagens) {
    // Bar chart: payments by month
    const ctxMes = document.getElementById('chartMes');
    if (ctxMes && porMes && porMes.length > 0) {
        new Chart(ctxMes, {
            type: 'bar',
            data: {
                labels: porMes.map(function(d) { return d.mes; }),
                datasets: [{
                    label: 'Valor (R$)',
                    data: porMes.map(function(d) { return d.total; }),
                    backgroundColor: 'rgba(13, 110, 253, 0.7)',
                    borderColor: 'rgba(13, 110, 253, 1)',
                    borderWidth: 1,
                    borderRadius: 6,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'R$ ' + context.parsed.y.toLocaleString('pt-BR', {
                                    minimumFractionDigits: 2
                                });
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return 'R$ ' + value.toLocaleString('pt-BR');
                            }
                        }
                    }
                }
            }
        });
    }

    // Doughnut chart: status distribution
    const ctxStatus = document.getElementById('chartStatus');
    if (ctxStatus && contagens) {
        const total = contagens.pago + contagens.pendente + contagens.atrasado + contagens.cancelado;
        if (total > 0) {
            new Chart(ctxStatus, {
                type: 'doughnut',
                data: {
                    labels: ['Pago', 'Pendente', 'Atrasado', 'Cancelado'],
                    datasets: [{
                        data: [contagens.pago, contagens.pendente, contagens.atrasado, contagens.cancelado],
                        backgroundColor: [
                            'rgba(25, 135, 84, 0.85)',
                            'rgba(255, 193, 7, 0.85)',
                            'rgba(220, 53, 69, 0.85)',
                            'rgba(108, 117, 125, 0.85)',
                        ],
                        borderWidth: 2,
                        borderColor: '#fff',
                    }]
                },
                options: {
                    responsive: true,
                    cutout: '65%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { padding: 12, font: { size: 12 } }
                        }
                    }
                }
            });
        }
    }
}
