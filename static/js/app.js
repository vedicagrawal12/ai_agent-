/**
 * LeadHunter AI — Frontend Application Entrypoint
 * 
 * Central coordinator bootstrapping state and managing event bindings.
 * Integrates search, leads, settings, and outreach ES6 modules.
 */

import { API } from './modules/api.js';
import { AppState } from './modules/state.js';
import { UI } from './modules/ui.js';
import { searchModule } from './modules/search.js';
import { leadsModule } from './modules/leads.js';
import { outreachModule } from './modules/outreach.js';
import { settingsModule } from './modules/settings.js';
import { analyticsModule } from './modules/analytics.js';

const App = {
    // Spread all modular methods into the central App controller
    ...searchModule,
    ...leadsModule,
    ...outreachModule,
    ...settingsModule,
    ...analyticsModule,

    // Local controller helper methods for UI panel slide/toggle transitions
    switchDetailTab(tabId) {
        // Toggle active visual class on tab buttons
        document.querySelectorAll('.detail-tab-btn').forEach(btn => {
            if (btn.getAttribute('data-tab') === tabId) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Toggle active visual class on content wrappers
        document.querySelectorAll('.detail-tab-content').forEach(wrapper => {
            if (wrapper.id === `detailTab-${tabId}`) {
                wrapper.classList.add('active');
            } else {
                wrapper.classList.remove('active');
            }
        });
    },

    closeDetailPane() {
        const detailPane = document.getElementById('detailPane');
        const backdrop = document.getElementById('detailPaneBackdrop');
        if (detailPane) {
            if (window.gsap) {
                if (window.innerWidth < 1024) {
                    window.gsap.to(detailPane, { yPercent: 100, duration: 0.4, ease: 'power2.in', overwrite: 'auto', onComplete: () => {
                        detailPane.classList.remove('active');
                        if (backdrop) backdrop.classList.remove('active');
                    }});
                } else {
                    window.gsap.to(detailPane, { 
                        xPercent: -50,
                        yPercent: -50,
                        scale: 0.9, 
                        opacity: 0, 
                        duration: 0.35, 
                        ease: 'power2.in', 
                        overwrite: 'auto', 
                        onComplete: () => {
                            detailPane.classList.remove('active');
                            if (backdrop) backdrop.classList.remove('active');
                        }
                    });
                }
                if (backdrop) {
                    window.gsap.to(backdrop, { opacity: 0, duration: 0.3, overwrite: 'auto' });
                }
            } else {
                detailPane.classList.remove('active');
                if (backdrop) backdrop.classList.remove('active');
            }
        }
    },

    bindEvents() {
        // Search form
        UI.el.searchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSearch();
        });

        // Deep Scan Toggle & City Input auto-suggest
        UI.el.deepScanToggle?.addEventListener('change', (e) => {
            UI.el.deepScanContainer.style.display = e.target.checked ? 'block' : 'none';
            if (e.target.checked && !UI.el.deepScanZonesInput.value.trim()) {
                this.suggestZones();
            }
        });

        UI.el.cityInput?.addEventListener('input', () => {
            if (UI.el.deepScanToggle?.checked) {
                this.suggestZones();
            }
        });

        // Settings modal
        document.getElementById('settingsBtn')?.addEventListener('click', () => {
            UI.openModal('settingsModal');
        });

        document.getElementById('historyBtn')?.addEventListener('click', async () => {
            await this.loadHistory();
            UI.openModal('historyModal');
        });

        // Close modals
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                const modal = btn.closest('.modal-overlay');
                if (modal) modal.classList.remove('active');
            });
        });

        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) overlay.classList.remove('active');
            });
        });

        // Detail Pane Close
        document.getElementById('closeDetailPaneBtn')?.addEventListener('click', () => {
            this.closeDetailPane();
        });

        // Close detail pane when clicking backdrop
        document.getElementById('detailPaneBackdrop')?.addEventListener('click', () => {
            this.closeDetailPane();
        });

        // Detail Pane Tab Switcher
        document.querySelectorAll('.detail-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.getAttribute('data-tab');
                this.switchDetailTab(tab);
            });
        });

        // Copy Mockup Link from Detail Pane
        document.getElementById('detailCopyMockupLinkBtn')?.addEventListener('click', () => {
            const lead = AppState.selectedLead;
            if (lead && lead.id) {
                this.copyMockupLink(lead.id);
            } else {
                UI.showToast('Select a lead to copy mockup link.', 'warning');
            }
        });

        // Save API key
        document.getElementById('saveApiKeyBtn')?.addEventListener('click', () => {
            this.saveApiKey();
        });

        // Save Portfolio URL
        UI.el.savePortfolioUrlBtn?.addEventListener('click', () => {
            this.savePortfolioUrl();
        });

        // Save Gemini API Key
        UI.el.saveGeminiApiKeyBtn?.addEventListener('click', () => {
            this.saveGeminiApiKey();
        });

        // Save Sender Profile
        UI.el.saveSenderProfileBtn?.addEventListener('click', () => {
            this.saveSenderProfile();
        });

        // Save Custom Pitch Rules
        UI.el.saveCustomPitchRulesBtn?.addEventListener('click', () => {
            this.saveCustomPitchRules();
        });

        // View Follow-ups Alert Banner Click
        UI.el.viewFollowupsBtn?.addEventListener('click', () => {
            this.openActiveReminders();
        });

        // Set reminder presets inside Schedule Reminder Modal
        document.querySelectorAll('.reminder-preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.reminder-preset-btn').forEach(b => b.classList.remove('selected'));
                e.target.classList.add('selected');
                
                // Keep styles dynamic
                document.querySelectorAll('.reminder-preset-btn').forEach(b => {
                    b.style.borderColor = '';
                    b.style.color = '';
                    b.style.background = '';
                });
                e.target.style.borderColor = 'var(--accent-orange)';
                e.target.style.color = 'var(--accent-orange)';
                e.target.style.background = 'rgba(249, 115, 22, 0.05)';
                
                // Clear custom date input if preset selected
                if (UI.el.customReminderDateInput) UI.el.customReminderDateInput.value = '';
            });
        });

        // Clear custom date select resets selected presets
        UI.el.customReminderDateInput?.addEventListener('input', () => {
            document.querySelectorAll('.reminder-preset-btn').forEach(b => {
                b.classList.remove('selected');
                b.style.borderColor = '';
                b.style.color = '';
                b.style.background = '';
            });
        });

        // Skip Reminder popup
        UI.el.skipReminderBtn?.addEventListener('click', () => {
            UI.closeModal('scheduleReminderModal');
        });

        // Save Reminder popup
        UI.el.saveReminderBtn?.addEventListener('click', () => {
            this.saveScheduledReminder();
        });

        // Save SMTP Settings
        UI.el.saveSmtpSettingsBtn?.addEventListener('click', () => {
            this.saveSmtpSettings();
        });

        // Save IMAP Settings
        document.getElementById('saveImapSettingsBtn')?.addEventListener('click', () => {
            this.saveImapSettings();
        });

        // Sync Replies on Demand
        document.getElementById('syncRepliesBtn')?.addEventListener('click', () => {
            this.syncReplies();
        });

        // Save Drip Settings
        document.getElementById('saveDripsSettingsBtn')?.addEventListener('click', () => {
            this.saveDripsSettings();
        });

        // AI Generate Email Pitch Button
        UI.el.aiGenerateEmailBtn?.addEventListener('click', () => {
            this.generateAIEmail();
        });

        // Native Mail Client (mailto:) Button
        UI.el.openMailClientBtn?.addEventListener('click', () => {
            this.openMailClient();
        });

        // Send Direct (SMTP) Email Button
        UI.el.sendSmtpEmailBtn?.addEventListener('click', () => {
            this.sendSMTPEmail();
        });

        // Scan Email on Demand button in modal
        UI.el.scanEmailOnDemandBtn?.addEventListener('click', () => {
            this.scanEmailOnDemand();
        });

        // AI Generate Pitch Button
        UI.el.aiGenerateBtn?.addEventListener('click', () => {
            this.generateAIPitch();
        });

        // Refine Pitch Button
        UI.el.refinePitchBtn?.addEventListener('click', () => {
            this.refineAIPitch();
        });

        // Custom Service selection toggles
        UI.el.pitchServiceSelect?.addEventListener('change', (e) => {
            if (e.target.value === 'custom') {
                if (UI.el.pitchCustomServiceContainer) UI.el.pitchCustomServiceContainer.style.display = 'block';
                if (UI.el.pitchCustomServiceInput) UI.el.pitchCustomServiceInput.focus();
            } else {
                if (UI.el.pitchCustomServiceContainer) UI.el.pitchCustomServiceContainer.style.display = 'none';
            }
        });

        UI.el.emailServiceSelect?.addEventListener('change', (e) => {
            if (e.target.value === 'custom') {
                if (UI.el.emailCustomServiceContainer) UI.el.emailCustomServiceContainer.style.display = 'block';
                if (UI.el.emailCustomServiceInput) UI.el.emailCustomServiceInput.focus();
            } else {
                if (UI.el.emailCustomServiceContainer) UI.el.emailCustomServiceContainer.style.display = 'none';
            }
        });

        // Bulk Scan Socials
        UI.el.bulkScanSocialsBtn?.addEventListener('click', () => {
            this.handleBulkScanSocials();
        });

        // Launch Email Outreach Campaign
        UI.el.bulkEmailCampaignBtn?.addEventListener('click', () => {
            this.openEmailCampaign();
        });

        // Campaign Custom Service selection toggles
        UI.el.campaignServiceSelect?.addEventListener('change', (e) => {
            if (e.target.value === 'custom') {
                if (UI.el.campaignCustomServiceContainer) UI.el.campaignCustomServiceContainer.style.display = 'block';
                if (UI.el.campaignCustomServiceInput) UI.el.campaignCustomServiceInput.focus();
            } else {
                if (UI.el.campaignCustomServiceContainer) UI.el.campaignCustomServiceContainer.style.display = 'none';
            }
        });

        // Campaign Autopilot Targeting toggle change
        document.getElementById('campaignAutopilotTargeting')?.addEventListener('change', (e) => {
            const isChecked = e.target.checked;
            const selectEl = document.getElementById('campaignServiceSelect');
            const customContainer = document.getElementById('campaignCustomServiceContainer');
            if (selectEl) {
                selectEl.disabled = isChecked;
                selectEl.style.opacity = isChecked ? '0.5' : '1';
            }
            if (customContainer) {
                customContainer.style.opacity = isChecked ? '0.5' : '1';
                const inputEl = document.getElementById('campaignCustomServiceInput');
                if (inputEl) inputEl.disabled = isChecked;
            }
        });

        // Bulk Scan Campaign Emails
        UI.el.campaignBulkScanBtn?.addEventListener('click', () => {
            this.bulkScanCampaignEmails();
        });
        
        // One-Click Autopilot Campaign
        UI.el.campaignAutopilotBtn?.addEventListener('click', () => {
            this.runAutopilotCampaign();
        });

        // Bulk Draft Campaign AI Emails
        UI.el.campaignBulkDraftBtn?.addEventListener('click', () => {
            this.bulkDraftCampaignAI();
        });

        // Bulk Send Campaign Emails
        UI.el.campaignBulkSendBtn?.addEventListener('click', () => {
            this.bulkSendCampaignSMTP();
        });

        // Selected campaign lead AI generate pitch button
        UI.el.campaignSelectedAIGenBtn?.addEventListener('click', () => {
            this.generateCampaignLeadAIDraft();
        });

        // Selected campaign lead Skip button
        UI.el.campaignSelectedSkipBtn?.addEventListener('click', () => {
            this.skipCampaignLead();
        });

        // Selected campaign lead Send button
        UI.el.campaignSelectedSendBtn?.addEventListener('click', () => {
            this.sendCampaignLeadSMTP();
        });

        // Interactive Live Preview text change listeners
        UI.el.campaignSubjectInput?.addEventListener('input', () => {
            this.updateCampaignLivePreview();
        });

        UI.el.campaignBodyInput?.addEventListener('input', () => {
            this.updateCampaignLivePreview();
        });

        // Clear Database
        document.getElementById('clearDbBtn')?.addEventListener('click', () => {
            this.clearDatabase();
        });

        // Export Excel
        document.getElementById('exportExcelBtn')?.addEventListener('click', () => {
            this.exportExcel();
        });

        // Load More Pagination
        document.getElementById('loadMoreBtn')?.addEventListener('click', () => {
            this.loadMoreLeads();
        });

        // View Switcher Tabs
        UI.el.listViewBtn?.addEventListener('click', () => {
            this.switchView('list');
        });

        UI.el.kanbanViewBtn?.addEventListener('click', () => {
            this.switchView('kanban');
        });

        document.getElementById('analyticsViewBtn')?.addEventListener('click', () => {
            this.switchView('analytics');
        });

        // Table sorting
        document.querySelectorAll('.leads-table th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                UI.sortLeads(th.dataset.sort);
            });
        });

        // WhatsApp template selection
        document.getElementById('templateOptions')?.addEventListener('change', (e) => {
            if (e.target.name === 'template') {
                AppState.selectedTemplate = e.target.value;
                this.updateMessagePreview();
                
                // Show/hide custom message area
                const customArea = document.getElementById('customMessageArea');
                if (customArea) {
                    customArea.style.display = e.target.value === 'custom' ? 'block' : 'none';
                }

                // Update selected visual styling class on template-option labels
                const container = document.getElementById('templateOptions');
                if (container) {
                    container.querySelectorAll('.template-option').forEach(o => o.classList.remove('selected'));
                    e.target.closest('.template-option')?.classList.add('selected');
                }
            }
        });

        // Custom message input
        document.getElementById('customMessageInput')?.addEventListener('input', () => {
            this.updateMessagePreview();
        });

        // Send WhatsApp button
        document.getElementById('sendWhatsAppBtn')?.addEventListener('click', () => {
            this.sendWhatsApp();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal-overlay.active').forEach(m => m.classList.remove('active'));
                this.closeDetailPane();
            }
            // Ctrl+K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                UI.el.queryInput.focus();
            }
        });
    },

    async init() {
        UI.init();
        this.bindEvents();
        
        // Fetch encryption key from backend for local credential storage security
        try {
            const keyResponse = await fetch('/api/encryption-key');
            if (keyResponse.ok) {
                const keyData = await keyResponse.json();
                AppState.encryptionKey = keyData.key;
            }
        } catch (error) {
            console.error('Failed to load session encryption key:', error);
        }

        await this.checkConfig();
        this.checkPortfolio();
        await this.checkGeminiConfig();
        this.checkSenderProfile();
        this.checkCustomPitchRules();
        await this.checkSmtpConfig();
        await this.checkImapConfig();
        await this.checkDripsConfig();
        this.loadReminders();
        await this.loadTemplates();
        if (AppState.currentView === 'analytics' && typeof this.fetchRecentDelivered === 'function') {
            this.fetchRecentDelivered();
        }
        
        // Initialize GSAP 3D card tilt hover effects
        UI.initTiltEffects();
        
        // Initial entry stagger animations
        if (window.gsap) {
            window.gsap.from('.app-header', { opacity: 0, y: -20, duration: 0.6, ease: 'power2.out' });
            window.gsap.from('.search-section', { opacity: 0, y: 30, duration: 0.7, delay: 0.15, ease: 'power2.out' });
            window.gsap.from('.search-form > *', { opacity: 0, y: 15, duration: 0.4, delay: 0.35, stagger: 0.08, ease: 'power1.out' });
        }
    }
};

// Expose globally for dynamic HTML callbacks (e.g. onclick="App.xxx(...)")
window.App = App;

// Bootstrap once the DOM is fully interactive
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
