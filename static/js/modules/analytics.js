/**
 * LeadHunter AI — Outreach Analytics Module
 * 
 * Fetches analytics telemetry from /api/stats/analytics and instantiates
 * premium responsive visual dashboards using Chart.js.
 */

import { API } from './api.js';
import { UI } from './ui.js';

let funnelChartInstance = null;
let ratiosChartInstance = null;
let timelineChartInstance = null;

export const analyticsModule = {
    async refreshAnalytics() {
        const funnelCanvas = document.getElementById('outreachFunnelChart');
        const ratiosCanvas = document.getElementById('telemetryRatiosChart');
        const timelineCanvas = document.getElementById('outreachTimelineChart');
        
        if (!funnelCanvas || !ratiosCanvas || !timelineCanvas) {
            console.warn('[Analytics] Chart canvases not found in DOM.');
            return;
        }

        try {
            const data = await API.request('/api/stats/analytics', {
                method: 'GET'
            });

            if (!data || !data.success) {
                console.error('[Analytics] Failed to fetch statistics.', data);
                return;
            }

            this.renderFunnelChart(funnelCanvas, data);
            this.renderRatiosChart(ratiosCanvas, data);
            this.renderTimelineChart(timelineCanvas, data);
        } catch (error) {
            console.error('[Analytics] Error loading stats: ', error);
            UI.showToast('Failed to populate Outreach Analytics dashboard.', 'error');
        }
    },

    renderFunnelChart(canvas, data) {
        if (funnelChartInstance) {
            funnelChartInstance.destroy();
        }

        const ctx = canvas.getContext('2d');
        const funnel = data.funnel || { scouted: 0, pitched: 0, opened: 0, clicked: 0, replied: 0, closed: 0 };
        
        funnelChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Scouted', 'Pitched', 'Opened', 'Clicked', 'Replied', 'Converted'],
                datasets: [{
                    label: 'Leads',
                    data: [funnel.scouted, funnel.pitched, funnel.opened, funnel.clicked, funnel.replied, funnel.closed],
                    backgroundColor: [
                        'rgba(148, 163, 184, 0.45)', // Scouted (grey-slate)
                        'rgba(139, 92, 246, 0.55)',  // Pitched (neon-violet)
                        'rgba(59, 130, 246, 0.55)',  // Opened (neon-blue)
                        'rgba(245, 158, 11, 0.55)',  // Clicked (neon-amber)
                        'rgba(6, 182, 212, 0.55)',   // Replied (neon-cyan)
                        'rgba(16, 185, 129, 0.65)'   // Converted (neon-green)
                    ],
                    borderColor: [
                        '#94a3b8',
                        '#8b5cf6',
                        '#3b82f6',
                        '#f59e0b',
                        '#06b6d4',
                        '#10b981'
                    ],
                    borderWidth: 1.5,
                    borderRadius: 5
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#e2e8f0',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#e2e8f0', font: { weight: 'bold' } }
                    }
                }
            }
        });
    },

    renderRatiosChart(canvas, data) {
        if (ratiosChartInstance) {
            ratiosChartInstance.destroy();
        }

        const ctx = canvas.getContext('2d');
        const total = data.ratios.total_sent || 0;
        const opened = data.ratios.total_opened || 0;
        const clicked = data.ratios.total_clicked || 0;
        const replied = data.ratios.total_replied || 0;

        // Secure subset hierarchy
        const cleanOpened = Math.max(opened, clicked);
        const cleanClicked = Math.max(clicked, replied);

        const unopenedVal = Math.max(0, total - cleanOpened);
        const openedVal = Math.max(0, cleanOpened - cleanClicked);
        const clickedVal = Math.max(0, cleanClicked - replied);
        const repliedVal = replied;

        ratiosChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Unopened', 'Opened (No Click)', 'Clicked (No Reply)', 'Replied'],
                datasets: [{
                    data: [unopenedVal, openedVal, clickedVal, repliedVal],
                    backgroundColor: [
                        'rgba(71, 85, 105, 0.4)',  // slate
                        'rgba(59, 130, 246, 0.55)', // blue
                        'rgba(245, 158, 11, 0.55)', // amber
                        'rgba(6, 182, 212, 0.55)'   // cyan
                    ],
                    borderColor: [
                        '#475569',
                        '#3b82f6',
                        '#f59e0b',
                        '#06b6d4'
                    ],
                    borderWidth: 1.5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#e2e8f0', boxWidth: 12, font: { size: 11 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const val = context.raw;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return ` ${context.label}: ${val} (${pct}%)`;
                            }
                        },
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#e2e8f0',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1
                    }
                },
                cutout: '65%'
            }
        });
    },

    renderTimelineChart(canvas, data) {
        if (timelineChartInstance) {
            timelineChartInstance.destroy();
        }

        const ctx = canvas.getContext('2d');
        const timeline = data.timeline || [];
        
        const dates = timeline.map(t => {
            const dateObj = new Date(t.date);
            return dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
        });
        const emails = timeline.map(t => t.email);
        const whatsapps = timeline.map(t => t.whatsapp);

        timelineChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Emails Sent',
                        data: emails,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.08)',
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2,
                        pointBackgroundColor: '#3b82f6'
                    },
                    {
                        label: 'WhatsApp Sent',
                        data: whatsapps,
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.08)',
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2,
                        pointBackgroundColor: '#10b981'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#e2e8f0' } },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#fff',
                        bodyColor: '#e2e8f0',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: { color: '#94a3b8' }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.04)' },
                        ticks: { color: '#94a3b8', stepSize: 1 }
                    }
                }
            }
        });
    }
};
