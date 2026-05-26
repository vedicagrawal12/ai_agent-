/**
 * AI Lead Generation Agent — Frontend Application
 * 
 * Handles search, results display, WhatsApp messaging,
 * CSV export, settings, and all UI interactions.
 */

// ============================================================
// State Management
// ============================================================
const AppState = {
    leads: [],
    allResults: [],
    stats: {},
    sortColumn: null,
    sortDirection: 'asc',
    selectedTemplate: 'website_pitch',
    whatsappTemplates: {},
    currentWhatsAppLead: null,
    isLoading: false,
    hasApiKey: false,
    currentOffset: 0,
    activeSearchParams: null,
    currentView: 'list'
};

// ============================================================
// API Client
// ============================================================
const API = {
    baseUrl: '',

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        // Merge headers properly to prevent options.headers from overwriting Content-Type
        const mergedHeaders = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };

        const config = {
            ...options,
            headers: mergedHeaders
        };

        // Automatically inject local storage API key if available
        const localKey = localStorage.getItem('serpapi_key');
        if (localKey) {
            config.headers['X-SerpApi-Key'] = localKey;
        }

        try {
            const response = await fetch(url, config);
            
            // Check if response is not OK first
            if (!response.ok) {
                let errorMessage = `Request failed with status ${response.status}`;
                try {
                    const data = await response.json();
                    errorMessage = data.error || errorMessage;
                } catch (_) {
                    // Fallback if response body is not JSON (e.g. 404 HTML from Live Server)
                    if (response.status === 404) {
                        errorMessage = `API endpoint not found (404). If you are using VS Code 'Go Live' (Live Server), please close it. Instead, run the backend server with 'python app.py' and open http://localhost:5000 in your browser.`;
                    }
                }
                throw new Error(errorMessage);
            }
            
            // Attempt to parse JSON response
            try {
                return await response.json();
            } catch (jsonError) {
                throw new Error(`Invalid server response (not valid JSON). If you are using VS Code 'Go Live' (Live Server), please close it. Instead, run the backend server with 'python app.py' and open http://localhost:5000 in your browser.`);
            }
        } catch (error) {
            if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
                throw new Error('Cannot connect to server. Please make sure the Flask backend is running (run "python app.py") and access via http://localhost:5000.');
            }
            throw error;
        }
    },

    async search(query, city, maxResults = 20, includeWithWebsite = false, hideSaved = false, deepScan = false, zones = [], startOffset = 0) {
        return this.request('/api/search', {
            method: 'POST',
            body: JSON.stringify({ 
                query, 
                city, 
                max_results: maxResults, 
                include_with_website: includeWithWebsite,
                hide_saved: hideSaved,
                deep_scan: deepScan,
                zones: zones,
                start_offset: startOffset
            }),
        });
    },

    async getConfig() {
        return this.request('/api/config');
    },

    async saveConfig(apiKey) {
        return this.request('/api/config/validate', {
            method: 'POST',
            body: JSON.stringify({ api_key: apiKey }),
        });
    },

    async clearDb() {
        return this.request('/api/config/clear-db', {
            method: 'POST'
        });
    },

    async getTemplates() {
        return this.request('/api/whatsapp/templates');
    },

    async generateWhatsAppLink(phone, template, lead, customMessage = '') {
        return this.request('/api/whatsapp/generate', {
            method: 'POST',
            body: JSON.stringify({ phone, template, lead, custom_message: customMessage }),
        });
    },

    async updateLeadPipelineStage(leadId, stage) {
        return this.request(`/api/leads/${leadId}/pipeline`, {
            method: 'POST',
            body: JSON.stringify({ stage }),
        });
    },

    async exportExcel(leads) {
        const response = await fetch('/api/export/excel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ leads }),
        });
        
        if (!response.ok) {
            throw new Error('Export failed');
        }
        
        const blob = await response.blob();
        return blob;
    },

    async getStats() {
        return this.request('/api/stats');
    },

    async getHistory() {
        return this.request('/api/history');
    },

    async getSavedLeads(priority = null, city = null) {
        const params = new URLSearchParams();
        if (priority) params.append('priority', priority);
        if (city) params.append('city', city);
        return this.request(`/api/leads?${params.toString()}`);
    }
};

// ============================================================
// UI Components
// ============================================================
const UI = {
    // Elements cache
    el: {},

    init() {
        // Cache DOM elements
        this.el = {
            searchForm: document.getElementById('searchForm'),
            queryInput: document.getElementById('queryInput'),
            cityInput: document.getElementById('cityInput'),
            maxResultsSelect: document.getElementById('maxResults'),
            searchBtn: document.getElementById('searchBtn'),
            includeWebsiteToggle: document.getElementById('includeWebsite'),
            hideSavedLeadsToggle: document.getElementById('hideSavedLeads'),
            deepScanToggle: document.getElementById('deepScan'),
            deepScanContainer: document.getElementById('deepScanContainer'),
            deepScanZonesInput: document.getElementById('deepScanZones'),
            
            statsBar: document.getElementById('statsBar'),
            statTotalFound: document.getElementById('statTotalFound'),
            statLeadsCount: document.getElementById('statLeadsCount'),
            statBrokenWebsites: document.getElementById('statBrokenWebsites'),
            statHighPriority: document.getElementById('statHighPriority'),
            statMediumPriority: document.getElementById('statMediumPriority'),
            statWithPhone: document.getElementById('statWithPhone'),
            statWithWhatsApp: document.getElementById('statWithWhatsApp'),
            
            resultsSection: document.getElementById('resultsSection'),
            resultsTitle: document.getElementById('resultsTitle'),
            leadsTableBody: document.getElementById('leadsTableBody'),
            emptyState: document.getElementById('emptyState'),
            tableContainer: document.getElementById('tableContainer'),
            loadMoreContainer: document.getElementById('loadMoreContainer'),
            loadMoreBtn: document.getElementById('loadMoreBtn'),
            
            loadingOverlay: document.getElementById('loadingOverlay'),
            loadingText: document.getElementById('loadingText'),
            
            settingsModal: document.getElementById('settingsModal'),
            apiKeyInput: document.getElementById('apiKeyInput'),
            apiKeyStatus: document.getElementById('apiKeyStatus'),
            portfolioUrlInput: document.getElementById('portfolioUrlInput'),
            savePortfolioUrlBtn: document.getElementById('savePortfolioUrlBtn'),
            portfolioStatus: document.getElementById('portfolioStatus'),
            geminiApiKeyInput: document.getElementById('geminiApiKeyInput'),
            saveGeminiApiKeyBtn: document.getElementById('saveGeminiApiKeyBtn'),
            geminiApiKeyStatus: document.getElementById('geminiApiKeyStatus'),
            
            // Sender Profile elements
            senderNameInput: document.getElementById('senderNameInput'),
            senderBrandInput: document.getElementById('senderBrandInput'),
            senderRoleInput: document.getElementById('senderRoleInput'),
            saveSenderProfileBtn: document.getElementById('saveSenderProfileBtn'),
            
            // Custom Pitch Rules elements
            customPitchRulesInput: document.getElementById('customPitchRulesInput'),
            saveCustomPitchRulesBtn: document.getElementById('saveCustomPitchRulesBtn'),
            customPitchRulesStatus: document.getElementById('customPitchRulesStatus'),
            
            // Reminders & Follow-up elements
            followupRemindersBanner: document.getElementById('followupRemindersBanner'),
            followupRemindersText: document.getElementById('followupRemindersText'),
            viewFollowupsBtn: document.getElementById('viewFollowupsBtn'),
            followupsModal: document.getElementById('followupsModal'),
            followupsListContainer: document.getElementById('followupsListContainer'),
            scheduleReminderModal: document.getElementById('scheduleReminderModal'),
            reminderLeadName: document.getElementById('reminderLeadName'),
            customReminderDateInput: document.getElementById('customReminderDateInput'),
            skipReminderBtn: document.getElementById('skipReminderBtn'),
            saveReminderBtn: document.getElementById('saveReminderBtn'),
            
            // SMTP Settings elements
            smtpHostInput: document.getElementById('smtpHostInput'),
            smtpPortInput: document.getElementById('smtpPortInput'),
            smtpEmailInput: document.getElementById('smtpEmailInput'),
            smtpPasswordInput: document.getElementById('smtpPasswordInput'),
            smtpUseSSL: document.getElementById('smtpUseSSL'),
            saveSmtpSettingsBtn: document.getElementById('saveSmtpSettingsBtn'),
            smtpStatus: document.getElementById('smtpStatus'),
            
            whatsappModal: document.getElementById('whatsappModal'),
            templateOptions: document.getElementById('templateOptions'),
            pitchToneSelect: document.getElementById('pitchToneSelect'),
            pitchLengthSelect: document.getElementById('pitchLengthSelect'),
            aiGenerateBtn: document.getElementById('aiGenerateBtn'),
            messagePreview: document.getElementById('messagePreview'),
            customMessageArea: document.getElementById('customMessageArea'),
            customMessageInput: document.getElementById('customMessageInput'),
            pitchRefineInput: document.getElementById('pitchRefineInput'),
            refinePitchBtn: document.getElementById('refinePitchBtn'),
            sendWhatsAppBtn: document.getElementById('sendWhatsAppBtn'),
            
            // Email Modal elements
            emailModal: document.getElementById('emailModal'),
            emailBusinessName: document.getElementById('emailBusinessName'),
            emailAddressText: document.getElementById('emailAddressText'),
            scanEmailOnDemandBtn: document.getElementById('scanEmailOnDemandBtn'),
            emailToneSelect: document.getElementById('emailToneSelect'),
            aiGenerateEmailBtn: document.getElementById('aiGenerateEmailBtn'),
            emailSubjectInput: document.getElementById('emailSubjectInput'),
            emailBodyInput: document.getElementById('emailBodyInput'),
            openMailClientBtn: document.getElementById('openMailClientBtn'),
            sendSmtpEmailBtn: document.getElementById('sendSmtpEmailBtn'),
            
            // Bulk Actions Elements
            bulkScanSocialsBtn: document.getElementById('bulkScanSocialsBtn'),
            bulkProgressBanner: document.getElementById('bulkProgressBanner'),
            bulkProgressLabel: document.getElementById('bulkProgressLabel'),
            bulkProgressPercentage: document.getElementById('bulkProgressPercentage'),
            bulkProgressBar: document.getElementById('bulkProgressBar'),
            bulkEmailCampaignBtn: document.getElementById('bulkEmailCampaignBtn'),
            
            // Campaign modal elements
            emailCampaignModal: document.getElementById('emailCampaignModal'),
            campaignStatLeads: document.getElementById('campaignStatLeads'),
            campaignStatEmails: document.getElementById('campaignStatEmails'),
            campaignStatDrafts: document.getElementById('campaignStatDrafts'),
            campaignStatSent: document.getElementById('campaignStatSent'),
            campaignBulkScanBtn: document.getElementById('campaignBulkScanBtn'),
            campaignBulkDraftBtn: document.getElementById('campaignBulkDraftBtn'),
            campaignBulkSendBtn: document.getElementById('campaignBulkSendBtn'),
            campaignProgressContainer: document.getElementById('campaignProgressContainer'),
            campaignProgressLabel: document.getElementById('campaignProgressLabel'),
            campaignProgressPercentage: document.getElementById('campaignProgressPercentage'),
            campaignProgressBar: document.getElementById('campaignProgressBar'),
            campaignTableBody: document.getElementById('campaignTableBody'),
            campaignOutboxReviewPanel: document.getElementById('campaignOutboxReviewPanel'),
            campaignOutboxEmptyState: document.getElementById('campaignOutboxEmptyState'),
            campaignOutboxWorkspace: document.getElementById('campaignOutboxWorkspace'),
            campaignSelectedName: document.getElementById('campaignSelectedName'),
            campaignSelectedEmail: document.getElementById('campaignSelectedEmail'),
            campaignSelectedPriority: document.getElementById('campaignSelectedPriority'),
            campaignSubjectInput: document.getElementById('campaignSubjectInput'),
            campaignBodyInput: document.getElementById('campaignBodyInput'),
            campaignSelectedAIGenBtn: document.getElementById('campaignSelectedAIGenBtn'),
            campaignSelectedSkipBtn: document.getElementById('campaignSelectedSkipBtn'),
            campaignSelectedSendBtn: document.getElementById('campaignSelectedSendBtn'),
            previewBusinessName: document.getElementById('previewBusinessName'),
            previewDeveloperBrand: document.getElementById('previewDeveloperBrand'),
            campaignEmailVisualPreview: document.getElementById('campaignEmailVisualPreview'),
            
            // Kanban elements
            listViewBtn: document.getElementById('listViewBtn'),
            kanbanViewBtn: document.getElementById('kanbanViewBtn'),
            kanbanContainer: document.getElementById('kanbanContainer'),
            
            toastContainer: document.getElementById('toastContainer'),
        };

        // AbortController for Kanban drag-and-drop listeners (prevents accumulation)
        this._kanbanAbortController = null;
    },

    // ---- Loading ----
    showLoading(message = 'Searching Google Maps...') {
        AppState.isLoading = true;
        this.el.loadingOverlay.classList.add('active');
        this.el.loadingText.textContent = message;
        this.el.searchBtn.disabled = true;
    },

    hideLoading() {
        AppState.isLoading = false;
        this.el.loadingOverlay.classList.remove('active');
        this.el.searchBtn.disabled = false;
    },

    // ---- Stats ----
    updateStats(stats) {
        this.el.statsBar.style.display = 'grid';
        this.el.statsBar.classList.add('fade-in');
        
        this.animateNumber(this.el.statTotalFound, stats.total_found || 0);
        this.animateNumber(this.el.statLeadsCount, stats.leads_count || 0);
        this.animateNumber(this.el.statBrokenWebsites, stats.broken_websites || 0);
        this.animateNumber(this.el.statHighPriority, stats.high_priority || 0);
        this.animateNumber(this.el.statMediumPriority, stats.medium_priority || 0);
        this.animateNumber(this.el.statWithPhone, stats.with_phone || 0);
        this.animateNumber(this.el.statWithWhatsApp, stats.with_whatsapp || 0);
    },

    animateNumber(element, target) {
        const duration = 600;
        const start = parseInt(element.textContent) || 0;
        const diff = target - start;
        const startTime = performance.now();

        function animate(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            element.textContent = Math.round(start + diff * eased);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        }
        
        requestAnimationFrame(animate);
    },

    // ---- Results Table ----
    renderLeads(leads) {
        AppState.leads = leads;
        
        this.el.resultsSection.style.display = 'block';
        this.el.resultsSection.classList.add('slide-up');
        
        if (leads.length === 0) {
            this.el.emptyState.style.display = 'block';
            this.el.tableContainer.style.display = 'none';
            if (this.el.kanbanContainer) this.el.kanbanContainer.style.display = 'none';
            if (this.el.loadMoreContainer) this.el.loadMoreContainer.style.display = 'none';
            return;
        }
        
        this.el.emptyState.style.display = 'none';
        
        // Show/hide container based on active view state
        if (AppState.currentView === 'kanban') {
            this.el.tableContainer.style.display = 'none';
            if (this.el.kanbanContainer) this.el.kanbanContainer.style.display = 'block';
            this.renderKanbanBoard(leads);
        } else {
            this.el.tableContainer.style.display = 'block';
            if (this.el.kanbanContainer) this.el.kanbanContainer.style.display = 'none';
            this.el.leadsTableBody.innerHTML = leads.map((lead, i) => this.createLeadRow(lead, i)).join('');
        }
        
        // Show/hide Load More button based on if we fetched any results
        if (this.el.loadMoreContainer) {
            const maxResults = AppState.activeSearchParams ? AppState.activeSearchParams.maxResults : 20;
            if (leads.length > 0 && leads.length % maxResults === 0) {
                this.el.loadMoreContainer.style.display = 'block';
            } else {
                this.el.loadMoreContainer.style.display = 'none';
            }
        }
    },

    createLeadRow(lead, index) {
        const priorityClass = `priority-${lead.priority.toLowerCase()}`;
        const priorityEmoji = { HIGH: '🔴', MEDIUM: '🟡', LOW: '🟢', IGNORE: '⚪' }[lead.priority] || '';
        const stars = this.renderStars(lead.rating);
        
        let phoneDisplay = lead.phone || '<span style="color: var(--text-muted)">N/A</span>';
        if (lead.phone && lead.line_type === 'LANDLINE') {
            phoneDisplay += ` <span class="landline-pill" data-tooltip="Landline Number (No WhatsApp)">Landline</span>`;
        }
        
        let websiteDisplay = '';
        if (lead.website) {
            const safeWebsite = this.escapeHtml(lead.website);
            if (lead.is_broken_website === 1) {
                websiteDisplay = `<a href="${safeWebsite}" target="_blank" class="broken-website-badge" data-tooltip="BROKEN SITE: ${safeWebsite}">⚠️ Broken Site</a>`;
            } else {
                websiteDisplay = `<a href="${safeWebsite}" target="_blank" class="website-link" data-tooltip="${safeWebsite}">🌐 Visit Site</a>`;
            }
        } else {
            websiteDisplay = `<span class="no-website">❌ No Website</span>`;
        }
            
        let whatsappBtn = '';
        if (lead.whatsapp_number) {
            if (lead.line_type === 'LANDLINE') {
                whatsappBtn = `<button class="row-btn whatsapp disabled-landline" data-tooltip="Landline Number (No WhatsApp)" disabled>💬</button>`;
            } else {
                whatsappBtn = `<button class="row-btn whatsapp" data-tooltip="Send WhatsApp" onclick="App.openWhatsApp(${index})">💬</button>`;
            }
        }

        let emailBtn = '';
        if (lead.email) {
            emailBtn = `<button class="row-btn email" data-tooltip="Send Email Outreach" onclick="App.openEmail(${index})">📧</button>`;
        } else {
            const tooltip = lead.website ? "Scan Website/Web for Email" : "Search Web for Email (SerpApi)";
            emailBtn = `<button class="row-btn scan-email-btn" id="scanEmailBtn-${index}" data-tooltip="${tooltip}" onclick="App.scanEmail(${lead.id}, ${index})">🔍📧</button>`;
        }
        
        // Build Google Maps search link
        const mapsQuery = encodeURIComponent(`${lead.name} ${lead.address || lead.city}`);
        const mapsLink = lead.place_id 
            ? `https://www.google.com/maps/search/?api=1&query=${mapsQuery}&query_place_id=${lead.place_id}`
            : `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`;
        
        let socialsDisplay = '';
        if (lead.instagram || lead.facebook) {
            if (lead.instagram) {
                socialsDisplay += `<button class="row-btn instagram" data-tooltip="Instagram DM & Auto-Copy" onclick="App.openInstagram(${index})" style="background: var(--gradient-primary); color: white; border: none; font-size: 0.75rem; padding: 3px 6px; border-radius: 4px; margin-right: 4px; cursor: pointer;">📸 DM</button>`;
            }
            if (lead.facebook) {
                socialsDisplay += `<a href="${lead.facebook}" target="_blank" class="row-btn facebook" data-tooltip="Facebook Profile" style="background: var(--accent-blue); color: white; font-size: 0.75rem; padding: 3px 6px; border-radius: 4px; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; height: 23px;">📘 Page</a>`;
            }
        } else {
            const scanId = lead.id || '';
            if (scanId) {
                socialsDisplay = `<button class="row-btn" id="scanSocialBtn-${index}" onclick="App.scanSocials(${scanId}, ${index})" style="font-size: 0.75rem; padding: 3px 6px; background: rgba(0,212,255,0.1); border: 1px solid var(--accent-cyan); color: var(--accent-cyan); border-radius: 4px; cursor: pointer;">🔍 Scan Socials</button>`;
            } else {
                socialsDisplay = `<span style="color: var(--text-muted); font-size: 0.8rem;">Save first to Scan</span>`;
            }
        }
 
        return `
            <tr>
                <td>
                    <div style="font-weight: 600;">${this.escapeHtml(lead.name)}</div>
                    <div class="category-pill" style="margin-top: 4px;">${this.escapeHtml(lead.category || 'Business')}</div>
                </td>
                <td class="phone-cell">${phoneDisplay}</td>
                <td>
                    <div class="truncate-address" data-tooltip="${this.escapeHtml(lead.address)}">${this.escapeHtml(lead.address || 'N/A')}</div>
                </td>
                <td>${this.escapeHtml(lead.city || 'N/A')}</td>
                <td>${websiteDisplay}</td>
                <td>
                    <div class="rating">
                        <span class="rating-stars">${stars}</span>
                        <span>${lead.rating || 'N/A'}</span>
                    </div>
                </td>
                <td>${lead.reviews || 0}</td>
                <td><span class="priority-badge ${priorityClass}">${priorityEmoji} ${lead.priority}</span></td>
                <td>${socialsDisplay}</td>
                <td>
                    <div class="row-actions">
                        <a href="${mapsLink}" target="_blank" class="row-btn" data-tooltip="View on Google Maps">📍</a>
                        ${whatsappBtn}
                        ${emailBtn}
                        <button class="row-btn mockup" data-tooltip="Copy Mockup Link" onclick="App.copyMockupLink(${lead.id})">📱</button>
                        <button class="row-btn" data-tooltip="Copy Phone" onclick="App.copyPhone(${index})">📋</button>
                    </div>
                </td>
            </tr>
        `;
    },

    renderStars(rating) {
        if (!rating) return '';
        const full = Math.floor(rating);
        const half = rating % 1 >= 0.5 ? 1 : 0;
        const empty = 5 - full - half;
        return '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(empty);
    },

    // ---- Kanban Board Renderers ----
    renderKanbanBoard(leads) {
        const columns = ['NEW', 'PITCHED', 'INTERESTED', 'CONVERTED', 'IGNORED'];
        
        // Clear all columns first
        columns.forEach(stage => {
            const cardsContainer = document.querySelector(`.kanban-cards[data-stage="${stage}"]`);
            if (cardsContainer) {
                cardsContainer.innerHTML = '';
            }
            const columnEl = document.querySelector(`.kanban-column[data-stage="${stage}"]`);
            const countBadge = columnEl?.querySelector('.column-count');
            if (countBadge) countBadge.textContent = '0';
        });
        
        // Track card counts per stage
        const counts = { NEW: 0, PITCHED: 0, INTERESTED: 0, CONVERTED: 0, IGNORED: 0 };
        
        leads.forEach(lead => {
            const stage = (lead.pipeline_stage || 'NEW').toUpperCase();
            if (!columns.includes(stage)) return;
            
            counts[stage]++;
            const cardsContainer = document.querySelector(`.kanban-cards[data-stage="${stage}"]`);
            if (cardsContainer) {
                const card = this.createKanbanCard(lead);
                cardsContainer.appendChild(card);
            }
        });
        
        // Update all badges
        columns.forEach(stage => {
            const columnEl = document.querySelector(`.kanban-column[data-stage="${stage}"]`);
            const countBadge = columnEl?.querySelector('.column-count');
            if (countBadge) {
                countBadge.textContent = counts[stage];
            }
        });
        
        // Initialize HTML5 Drag-and-Drop listeners
        this.initKanbanDragAndDrop();
    },

    createKanbanCard(lead) {
        const card = document.createElement('div');
        card.className = 'kanban-card';
        card.setAttribute('draggable', 'true');
        card.setAttribute('data-id', lead.id);
        
        const priorityClass = (lead.priority || 'LOW').toUpperCase();
        
        // Determine site label
        let siteLabel = '';
        if (lead.is_broken_website === 1) {
            siteLabel = `<span style="color: var(--accent-red); font-size: 0.7rem; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">⚠️ Broken site</span>`;
        } else if (lead.website) {
            siteLabel = `<span style="color: var(--accent-green); font-size: 0.7rem; font-weight: 500;">✓ Website</span>`;
        } else {
            siteLabel = `<span style="color: var(--text-muted); font-size: 0.7rem;">No website</span>`;
        }
        
        let actionsHtml = '';
        const idx = AppState.leads.findIndex(l => l.id === lead.id);
        
        // Scan or show Socials
        if (lead.instagram || lead.facebook) {
            if (lead.instagram) {
                actionsHtml += `<button class="kanban-card-btn instagram" title="Instagram DM & Auto-Copy" onclick="App.openInstagram(${idx})" style="background: var(--gradient-primary); color: white; border-radius: 4px; padding: 4px 8px; font-size: 0.75rem; font-weight: 600; border: none; display: flex; align-items: center; gap: 4px; cursor: pointer;">📸 DM</button>`;
            }
            if (lead.facebook) {
                actionsHtml += `<a href="${lead.facebook}" target="_blank" class="kanban-card-btn facebook" title="Facebook Profile" style="background: var(--accent-blue); color: white; border-radius: 4px; padding: 4px 8px; font-size: 0.75rem; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; height: 25px;">📘 Page</a>`;
            }
        } else if (lead.id) {
            actionsHtml += `<button class="kanban-card-btn scan-social" onclick="App.scanSocials(${lead.id}, ${idx})" style="font-size: 0.75rem; padding: 4px 8px; background: rgba(0,212,255,0.1); border: 1px solid var(--accent-cyan); color: var(--accent-cyan); border-radius: 4px; cursor: pointer;">🔍 Scan Socials</button>`;
        }
        
        // WhatsApp button
        let whatsappBtnHtml = '';
        if (lead.whatsapp_number) {
            if (lead.line_type === 'LANDLINE') {
                whatsappBtnHtml = `<button class="kanban-card-btn whatsapp disabled-landline" title="Landline Number (No WhatsApp)" style="background: rgba(255,255,255,0.05); color: var(--text-muted); border-radius: 4px; padding: 4px 8px; border: 1px solid var(--border-color); font-size: 0.75rem; cursor: not-allowed;" disabled>💬 Pitch</button>`;
            } else {
                whatsappBtnHtml = `<button class="kanban-card-btn whatsapp" title="Personalized WhatsApp Pitch" onclick="App.openWhatsApp(${idx})" style="background: var(--gradient-whatsapp); color: white; border-radius: 4px; padding: 4px 8px; border: none; font-size: 0.75rem; font-weight: 600; display: flex; align-items: center; gap: 4px; cursor: pointer;">💬 Pitch</button>`;
            }
        }

        let emailBtnHtml = '';
        if (lead.email) {
            emailBtnHtml = `<button class="kanban-card-btn email" title="Send Email Pitch" onclick="App.openEmail(${idx})" style="background: var(--gradient-primary); color: white; border: none; font-size: 0.75rem; padding: 4px 8px; border-radius: 4px; display: inline-flex; align-items: center; gap: 4px; cursor: pointer;">📧 Email</button>`;
        } else {
            const btnTitle = lead.website ? "Scan Website/Web for Email" : "Search Web for Email (SerpApi)";
            emailBtnHtml = `<button class="kanban-card-btn scan-email" id="kanbanScanEmailBtn-${idx}" onclick="App.scanEmail(${lead.id}, ${idx})" style="font-size: 0.75rem; padding: 4px 8px; background: rgba(0,240,255,0.1); border: 1px solid var(--accent-cyan); color: var(--accent-cyan); border-radius: 4px; cursor: pointer;" title="${btnTitle}">🔍 Email</button>`;
        }
        
        card.innerHTML = `
            <div class="kanban-card-title" title="${lead.name}">${lead.name}</div>
            <div class="kanban-card-category">${lead.category || 'Local Business'}</div>
            <div class="kanban-card-meta">
                <div>📞 ${lead.phone || 'No phone'}</div>
                <div>📍 ${lead.city || 'Local'}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%; margin-top: 4px;">
                    <div>⭐ ${lead.rating ? lead.rating.toFixed(1) : '0.0'} (${lead.reviews || 0})</div>
                    ${siteLabel}
                </div>
                <div class="kanban-card-priority-badge ${priorityClass}">${priorityClass} Priority</div>
            </div>
            <div class="kanban-card-actions" style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                    ${actionsHtml}
                    ${emailBtnHtml}
                    <button class="kanban-card-btn mockup" title="Copy Live Mockup Link" onclick="App.copyMockupLink(${lead.id})">📱 Mockup</button>
                </div>
                ${whatsappBtnHtml}
            </div>
        `;
        
        return card;
    },

    initKanbanDragAndDrop() {
        // Abort previous listeners to prevent accumulation (BUG #1 fix)
        if (this._kanbanAbortController) {
            this._kanbanAbortController.abort();
        }
        this._kanbanAbortController = new AbortController();
        const signal = this._kanbanAbortController.signal;

        const cards = document.querySelectorAll('.kanban-card');
        const columns = document.querySelectorAll('.kanban-column');
        
        cards.forEach(card => {
            card.addEventListener('dragstart', (e) => {
                card.classList.add('dragging');
                e.dataTransfer.setData('text/plain', card.getAttribute('data-id'));
            }, { signal });
            
            card.addEventListener('dragend', () => {
                card.classList.remove('dragging');
            }, { signal });
        });
        
        columns.forEach(column => {
            column.addEventListener('dragover', (e) => {
                e.preventDefault();
                column.classList.add('drag-over');
            }, { signal });
            
            column.addEventListener('dragleave', () => {
                column.classList.remove('drag-over');
            }, { signal });
            
            column.addEventListener('drop', async (e) => {
                e.preventDefault();
                column.classList.remove('drag-over');
                
                const leadId = parseInt(e.dataTransfer.getData('text/plain'));
                const newStage = column.getAttribute('data-stage');
                
                if (!leadId || !newStage) return;
                
                const lead = AppState.leads.find(l => l.id === leadId);
                if (!lead) return;
                
                const oldStage = lead.pipeline_stage || 'NEW';
                if (oldStage.toUpperCase() === newStage.toUpperCase()) return;
                
                try {
                    // Update state locally first for snappy responsiveness
                    lead.pipeline_stage = newStage;
                    
                    // If transitioning to PITCHED, also set contacted = 1 and contact_date locally
                    if (newStage === 'PITCHED') {
                        lead.contacted = 1;
                        if (!lead.contact_date) {
                            lead.contact_date = new Date().toISOString();
                        }
                    }
                    
                    // Re-render immediately
                    UI.renderLeads(AppState.leads);
                    
                    // Sync with database
                    const data = await API.updateLeadPipelineStage(leadId, newStage);
                    if (data.success) {
                        UI.showToast(`Updated "${lead.name}" pipeline stage to ${newStage}!`, 'success');
                    } else {
                        throw new Error(data.error || 'Sync failed');
                    }
                } catch (err) {
                    console.error('Failed to sync Kanban stage:', err);
                    UI.showToast(`Stage sync failed: ${err.message}. Reverting...`, 'error');
                    // Revert state
                    lead.pipeline_stage = oldStage;
                    UI.renderLeads(AppState.leads);
                }
            }, { signal });
        });
    },

    // ---- Sorting ----
    sortLeads(column) {
        if (AppState.sortColumn === column) {
            AppState.sortDirection = AppState.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            AppState.sortColumn = column;
            AppState.sortDirection = 'asc';
        }
        
        const priorityOrder = { HIGH: 0, MEDIUM: 1, LOW: 2, IGNORE: 3 };
        
        AppState.leads.sort((a, b) => {
            let valA = a[column];
            let valB = b[column];
            
            if (column === 'priority') {
                valA = priorityOrder[valA] || 3;
                valB = priorityOrder[valB] || 3;
            }
            
            if (typeof valA === 'string') valA = valA.toLowerCase();
            if (typeof valB === 'string') valB = valB.toLowerCase();
            
            if (valA < valB) return AppState.sortDirection === 'asc' ? -1 : 1;
            if (valA > valB) return AppState.sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
        
        // Update header classes
        document.querySelectorAll('.leads-table th').forEach(th => {
            th.classList.remove('sorted-asc', 'sorted-desc');
        });
        
        const clickedTh = document.querySelector(`.leads-table th[data-sort="${column}"]`);
        if (clickedTh) {
            clickedTh.classList.add(`sorted-${AppState.sortDirection}`);
        }
        
        this.renderLeads(AppState.leads);
    },

    // ---- Toasts ----
    showToast(message, type = 'info') {
        const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
        
        // Intercept SerpApi search quota limits exhaustion
        if (message && (message.includes('run out of searches') || message.includes('quota') || message.includes('SerpApi Error'))) {
            message = "⚠️ Aapka SerpApi Free Search Limit khatm ho gaya hai! Please Settings Panel (⚙️) me jakar naya free API key update karein.";
            type = 'error';
        }
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        // Use DOM API instead of innerHTML to prevent HTML injection (BUG #18 fix)
        const iconSpan = document.createElement('span');
        iconSpan.className = 'toast-icon';
        iconSpan.textContent = icons[type] || 'ℹ️';
        
        const msgSpan = document.createElement('span');
        msgSpan.className = 'toast-message';
        msgSpan.textContent = message;
        
        toast.appendChild(iconSpan);
        toast.appendChild(msgSpan);
        
        this.el.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('toast-exit');
            setTimeout(() => toast.remove(), 300);
        }, 6000); // Extended duration to 6s so the user can easily read the instruction
    },

    // ---- Modals ----
    openModal(modalId) {
        document.getElementById(modalId).classList.add('active');
    },

    closeModal(modalId) {
        document.getElementById(modalId).classList.remove('active');
    },

    escapeHtml(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
};

// ============================================================
// Predefined Sub-localities for Popular Indian Cities
// ============================================================
const SUB_LOCALITIES = {
    "bhopal": ["MP Nagar", "Kolar Road", "Arera Colony", "Indrapuri", "Awadhpuri"],
    "indore": ["Vijay Nagar", "Palasia", "Bhanwarkuan", "Rajendra Nagar", "Bengali Square"],
    "delhi": ["Connaught Place", "Karol Bagh", "Rajouri Garden", "Saket", "Dwarka"],
    "mumbai": ["Andheri West", "Bandra West", "Dadar", "Juhu", "Powai"],
    "bangalore": ["Koramangala", "Indiranagar", "HSR Layout", "Jayanagar", "Whitefield"],
    "pune": ["Kothrud", "Koregaon Park", "Hinjawadi", "Wakad", "Baner"],
    "jaipur": ["Malviya Nagar", "Vaishali Nagar", "C Scheme", "Mansarovar", "Raja Park"],
    "ahmedabad": ["Satellite", "C G Road", "Vastrapur", "Bodakdev", "Prahlad Nagar"],
    "lucknow": ["Hazratganj", "Gomti Nagar", "Aliganj", "Indira Nagar", "Charbagh"],
    "hyderabad": ["Gachibowli", "Madhapur", "Jubilee Hills", "Banjara Hills", "Kondapur"]
};

// ============================================================
// Application Controller
// ============================================================
const App = {
    async init() {
        UI.init();
        this.bindEvents();
        await this.checkConfig();
        this.checkPortfolio();
        this.checkGeminiConfig();
        this.checkSenderProfile();
        this.checkCustomPitchRules();
        this.checkSmtpConfig();
        this.loadReminders();
        await this.loadTemplates();
    },

    suggestZones() {
        const city = UI.el.cityInput.value.trim().toLowerCase();
        if (!city) {
            UI.el.deepScanZonesInput.value = '';
            return;
        }
        
        // Find matching key in SUB_LOCALITIES
        const matchedKey = Object.keys(SUB_LOCALITIES).find(k => k === city || city.includes(k));
        if (matchedKey) {
            UI.el.deepScanZonesInput.value = SUB_LOCALITIES[matchedKey].join(', ');
        } else {
            // Default directional zones if city not recognized
            const rawCity = UI.el.cityInput.value.trim();
            UI.el.deepScanZonesInput.value = `North ${rawCity}, South ${rawCity}, East ${rawCity}, West ${rawCity}, Central ${rawCity}`;
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
        document.getElementById('settingsBtn').addEventListener('click', () => {
            UI.openModal('settingsModal');
        });

        document.getElementById('historyBtn').addEventListener('click', async () => {
            await this.loadHistory();
            UI.openModal('historyModal');
        });

        // Close modals
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                const modal = btn.closest('.modal-overlay');
                modal.classList.remove('active');
            });
        });

        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) overlay.classList.remove('active');
            });
        });

        // Save API key
        document.getElementById('saveApiKeyBtn').addEventListener('click', () => {
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

        // Bulk Scan Socials
        UI.el.bulkScanSocialsBtn?.addEventListener('click', () => {
            this.handleBulkScanSocials();
        });

        // Launch Email Outreach Campaign
        UI.el.bulkEmailCampaignBtn?.addEventListener('click', () => {
            this.openEmailCampaign();
        });

        // Bulk Scan Campaign Emails
        UI.el.campaignBulkScanBtn?.addEventListener('click', () => {
            this.bulkScanCampaignEmails();
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
        document.getElementById('exportExcelBtn').addEventListener('click', () => {
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
            }
            // Ctrl+K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                UI.el.queryInput.focus();
            }
        });
    },

    // ---- Config ----
    async checkConfig() {
        try {
            const localKey = localStorage.getItem('serpapi_key');
            const data = await API.getConfig(); // Check if server has default key
            AppState.hasApiKey = !!localKey || data.has_api_key;
            
            // Update header status badge
            const statusEl = UI.el.apiKeyStatus;
            const settingsStatus = document.getElementById('settingsApiKeyStatus');
            
            if (localKey) {
                statusEl.className = 'api-key-status active';
                statusEl.textContent = '✓ Your Key';
                if (settingsStatus) {
                    settingsStatus.className = 'api-key-status active';
                    settingsStatus.textContent = '✓ Using Your Local API Key';
                }
            } else if (data.has_api_key) {
                statusEl.className = 'api-key-status active';
                statusEl.textContent = '✓ Connected';
                if (settingsStatus) {
                    settingsStatus.className = 'api-key-status active';
                    settingsStatus.textContent = '✓ Server Default Key Connected';
                }
            } else {
                statusEl.className = 'api-key-status inactive';
                statusEl.textContent = '✗ Not Set';
                if (settingsStatus) {
                    settingsStatus.className = 'api-key-status inactive';
                    settingsStatus.textContent = '✗ Not Set';
                }
            }
        } catch (error) {
            console.error('Config check failed:', error);
        }
    },

    async saveApiKey() {
        const apiKey = UI.el.apiKeyInput.value.trim();
        
        // If the user submits an empty key, it clears their local API key
        if (!apiKey) {
            localStorage.removeItem('serpapi_key');
            AppState.hasApiKey = false;
            UI.closeModal('settingsModal');
            await this.checkConfig();
            UI.showToast('Local API key cleared successfully!', 'info');
            return;
        }

        try {
            UI.showLoading('Validating API key...');
            await API.saveConfig(apiKey); // Test validation on server
            
            // Save key locally on browser
            localStorage.setItem('serpapi_key', apiKey);
            AppState.hasApiKey = true;
            UI.el.apiKeyInput.value = '';
            UI.closeModal('settingsModal');
            await this.checkConfig();
            UI.showToast('API key validated & saved locally!', 'success');
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    checkPortfolio() {
        const portfolioUrl = localStorage.getItem('portfolio_url');
        const statusEl = UI.el.portfolioStatus;
        if (portfolioUrl) {
            if (statusEl) {
                statusEl.className = 'api-key-status active';
                statusEl.textContent = '✓ Connected';
            }
            if (UI.el.portfolioUrlInput) {
                UI.el.portfolioUrlInput.value = portfolioUrl;
            }
        } else {
            if (statusEl) {
                statusEl.className = 'api-key-status inactive';
                statusEl.textContent = '✗ Not Set';
            }
        }
    },

    async savePortfolioUrl() {
        const portfolioUrl = UI.el.portfolioUrlInput.value.trim();
        
        // If the user submits an empty URL, it clears their local portfolio URL and projects
        if (!portfolioUrl) {
            localStorage.removeItem('portfolio_url');
            localStorage.removeItem('portfolio_projects');
            this.checkPortfolio();
            UI.showToast('Portfolio link cleared successfully!', 'info');
            return;
        }

        try {
            UI.showLoading('Scanning & parsing portfolio...');
            const data = await API.request('/api/portfolio/scan', {
                method: 'POST',
                body: JSON.stringify({ portfolio_url: portfolioUrl }),
            });
            
            if (data.success) {
                // Save URL and parsed projects locally in the browser
                localStorage.setItem('portfolio_url', data.portfolio_url);
                localStorage.setItem('portfolio_projects', JSON.stringify(data.projects || []));
                
                this.checkPortfolio();
                UI.showToast(`Portfolio scanned successfully! Found ${data.projects.length} project samples.`, 'success');
            } else {
                UI.showToast('Failed to scan portfolio.', 'error');
            }
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    checkGeminiConfig() {
        const geminiKey = localStorage.getItem('gemini_api_key');
        const statusEl = UI.el.geminiApiKeyStatus;
        if (geminiKey) {
            if (statusEl) {
                statusEl.className = 'api-key-status active';
                statusEl.textContent = '✓ Configured';
            }
            if (UI.el.geminiApiKeyInput) {
                UI.el.geminiApiKeyInput.value = geminiKey;
            }
        } else {
            if (statusEl) {
                statusEl.className = 'api-key-status inactive';
                statusEl.textContent = '✗ Not Set';
            }
        }
    },

    saveGeminiApiKey() {
        const geminiKey = UI.el.geminiApiKeyInput.value.trim();
        
        // If empty, clear the key
        if (!geminiKey) {
            localStorage.removeItem('gemini_api_key');
            this.checkGeminiConfig();
            UI.showToast('Gemini API key cleared successfully!', 'info');
            return;
        }

        // Save key in localStorage
        localStorage.setItem('gemini_api_key', geminiKey);
        this.checkGeminiConfig();
        UI.showToast('Gemini API key saved locally!', 'success');
    },

    checkSenderProfile() {
        const name = localStorage.getItem('sender_name') || '';
        const brand = localStorage.getItem('sender_brand') || '';
        const role = localStorage.getItem('sender_role') || '';
        
        if (UI.el.senderNameInput) UI.el.senderNameInput.value = name;
        if (UI.el.senderBrandInput) UI.el.senderBrandInput.value = brand;
        if (UI.el.senderRoleInput) UI.el.senderRoleInput.value = role;
    },

    saveSenderProfile() {
        const name = UI.el.senderNameInput?.value.trim() || '';
        const brand = UI.el.senderBrandInput?.value.trim() || '';
        const role = UI.el.senderRoleInput?.value.trim() || '';
        
        localStorage.setItem('sender_name', name);
        localStorage.setItem('sender_brand', brand);
        localStorage.setItem('sender_role', role);
        
        UI.showToast('Sender Profile saved successfully!', 'success');
    },

    checkCustomPitchRules() {
        const rules = localStorage.getItem('custom_pitch_rules') || '';
        if (UI.el.customPitchRulesInput) UI.el.customPitchRulesInput.value = rules;
        
        const statusEl = UI.el.customPitchRulesStatus;
        if (statusEl) {
            if (rules) {
                statusEl.textContent = '✓ Configured & Active';
                statusEl.className = 'api-key-status active';
            } else {
                statusEl.textContent = '✗ Not Set';
                statusEl.className = 'api-key-status inactive';
            }
        }
    },

    saveCustomPitchRules() {
        const rules = UI.el.customPitchRulesInput?.value.trim() || '';
        localStorage.setItem('custom_pitch_rules', rules);
        this.checkCustomPitchRules();
        UI.showToast('AI Pitch Custom Rules saved successfully!', 'success');
    },

    async generateAIPitch() {
        const lead = AppState.currentWhatsAppLead;
        if (!lead) return;

        const geminiKey = localStorage.getItem('gemini_api_key');
        if (!geminiKey) {
            UI.showToast('Please configure your Gemini API Key in Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const projectSample = this.getBestPortfolioProjectSample(lead);
        const tone = UI.el.pitchToneSelect?.value || 'elite';
        const length = UI.el.pitchLengthSelect?.value || 'detailed';

        try {
            UI.showLoading('AI Writer generating pitch...');
            
            // Call AI writer endpoint statelessly
            const data = await API.request('/api/outreach/generate-ai', {
                method: 'POST',
                headers: {
                    'X-Gemini-API-Key': geminiKey
                },
                body: JSON.stringify({
                    lead: lead,
                    project_sample: projectSample,
                    tone: tone,
                    length: length,
                    sender: {
                        name: localStorage.getItem('sender_name') || '',
                        brand: localStorage.getItem('sender_brand') || '',
                        role: localStorage.getItem('sender_role') || ''
                    },
                    custom_pitch_rules: localStorage.getItem('custom_pitch_rules') || ''
                })
            });

            if (data.success && data.pitch) {
                // Programmatically select "custom" template radio button
                const customRadio = document.querySelector('input[name="template"][value="custom"]');
                if (customRadio) {
                    customRadio.checked = true;
                    AppState.selectedTemplate = 'custom';
                    
                    // Show custom message textarea
                    const customArea = document.getElementById('customMessageArea');
                    if (customArea) customArea.style.display = 'block';
                    
                    // Highlight selected radio visual option
                    const container = UI.el.templateOptions;
                    if (container) {
                        container.querySelectorAll('.template-option').forEach(o => o.classList.remove('selected'));
                        customRadio.closest('.template-option')?.classList.add('selected');
                    }
                }

                // Populate custom message input box with the AI generated pitch
                const customMessageInput = document.getElementById('customMessageInput');
                if (customMessageInput) {
                    customMessageInput.value = data.pitch;
                }

                // Refresh preview panel
                this.updateMessagePreview();
                UI.showToast('✨ Unique AI Sales pitch generated successfully!', 'success');
            }
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async refineAIPitch() {
        const lead = AppState.currentWhatsAppLead;
        if (!lead) return;

        const geminiKey = localStorage.getItem('gemini_api_key');
        if (!geminiKey) {
            UI.showToast('Please configure your Gemini API Key in Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const customMessageInput = document.getElementById('customMessageInput');
        const previousPitch = customMessageInput?.value.trim() || '';
        const refineFeedback = UI.el.pitchRefineInput?.value.trim() || '';

        if (!refineFeedback) {
            UI.showToast('Please enter some refinement feedback first!', 'warning');
            return;
        }

        const projectSample = this.getBestPortfolioProjectSample(lead);
        const tone = UI.el.pitchToneSelect?.value || 'elite';
        const length = UI.el.pitchLengthSelect?.value || 'detailed';

        try {
            UI.showLoading('AI Writer refining pitch...');
            
            const data = await API.request('/api/outreach/generate-ai', {
                method: 'POST',
                headers: {
                    'X-Gemini-API-Key': geminiKey
                },
                body: JSON.stringify({
                    lead: lead,
                    project_sample: projectSample,
                    tone: tone,
                    length: length,
                    sender: {
                        name: localStorage.getItem('sender_name') || '',
                        brand: localStorage.getItem('sender_brand') || '',
                        role: localStorage.getItem('sender_role') || ''
                    },
                    refine_feedback: refineFeedback,
                    previous_pitch: previousPitch,
                    custom_pitch_rules: localStorage.getItem('custom_pitch_rules') || ''
                })
            });

            if (data.success && data.pitch) {
                if (customMessageInput) {
                    customMessageInput.value = data.pitch;
                }
                
                // Clear the refine input
                if (UI.el.pitchRefineInput) {
                    UI.el.pitchRefineInput.value = '';
                }

                this.updateMessagePreview();
                UI.showToast('Pitch refined successfully!', 'success');
            } else {
                UI.showToast(data.error || 'Failed to refine pitch.', 'error');
            }
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async clearDatabase() {
        if (!confirm("Kya aap sach mein database clean karna chahte hain?\n\n(Isse sirf uncontacted leads aur search history clear hogi, aapka contacted leads record safe rahega.)")) {
            return;
        }

        try {
            UI.showLoading('Cleaning database...');
            const data = await API.clearDb();
            if (data.success) {
                UI.showToast(`Database cleaned! Deleted ${data.leads_deleted} leads and search history.`, 'success');
                UI.closeModal('settingsModal');
                
                // Refresh table if active
                if (AppState.leads.length > 0) {
                    AppState.leads = [];
                    AppState.allResults = [];
                    UI.renderLeads([]);
                }
            } else {
                UI.showToast('Clean failed: ' + (data.error || 'Unknown error'), 'error');
            }
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async scanSocials(leadId, index) {
        const btn = document.getElementById(`scanSocialBtn-${index}`);
        if (btn) {
            btn.innerHTML = '⏳ Scanning...';
            btn.disabled = true;
        }

        try {
            const data = await API.request(`/api/leads/${leadId}/scan-socials`, {
                method: 'POST'
            });

            if (data.success) {
                // Update AppState lead data
                AppState.leads[index].instagram = data.instagram || '';
                AppState.leads[index].facebook = data.facebook || '';
                
                // Also update allResults if matching
                const placeId = AppState.leads[index].place_id;
                const matchedAll = AppState.allResults.find(l => l.place_id === placeId);
                if (matchedAll) {
                    matchedAll.instagram = data.instagram || '';
                    matchedAll.facebook = data.facebook || '';
                }

                if (data.instagram || data.facebook) {
                    let msg = 'Found:';
                    if (data.instagram) msg += ' 📸 Instagram';
                    if (data.facebook) msg += ' 📘 Facebook';
                    UI.showToast(msg, 'success');
                } else {
                    UI.showToast('No social profiles found for this business on Google.', 'info');
                }

                // Re-render leads to show new buttons
                UI.renderLeads(AppState.leads);
            }
        } catch (error) {
            UI.showToast('Scan failed: ' + error.message, 'error');
            if (btn) {
                btn.innerHTML = '🔍 Scan Socials';
                btn.disabled = false;
            }
        }
    },

    async openInstagram(index) {
        const lead = AppState.leads[index];
        if (!lead || !lead.instagram) {
            UI.showToast('No Instagram profile link available', 'error');
            return;
        }

        // Build pitch message: always use default template for Instagram DM (BUG #16 fix)
        // Don't rely on WhatsApp modal's stale selectedTemplate state
        let message = '';
        
        // If lead already has a custom AI pitch saved, use that
        if (lead.custom_pitch) {
            message = lead.custom_pitch;
        } else {
            // Use default website_pitch template
            const templateData = AppState.whatsappTemplates['website_pitch'];
            message = templateData ? templateData.message : 'Hello {business_name}!';
        }

        // Replace template variables dynamically for this lead
        const projectSampleText = this.getBestPortfolioProjectSample(lead);
        message = message
            .replace(/\{business_name\}/g, lead.name || 'there')
            .replace(/\{city\}/g, lead.city || 'your city')
            .replace(/\{category\}/g, lead.category || 'business')
            .replace(/\{rating\}/g, lead.rating || 'great')
            .replace(/\{reviews\}/g, (lead.reviews !== undefined && lead.reviews !== null) ? lead.reviews : 'many')
            .replace(/\{address\}/g, lead.address || '')
            .replace(/\{phone\}/g, lead.phone || '')
            .replace(/\{project_sample\}/g, projectSampleText);

        try {
            // Copy pitch to clipboard
            await navigator.clipboard.writeText(message);
            UI.showToast('📋 Pitch copied to clipboard! Opening Instagram...', 'success');
        } catch (clipErr) {
            // Fallback copy
            const textArea = document.createElement('textarea');
            textArea.value = message;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            UI.showToast('📋 Pitch copied to clipboard! Opening Instagram...', 'success');
        }

        // Open Instagram profile in a new tab
        setTimeout(() => {
            // Open direct message window if possible, else open profile
            // Instagram profile link looks like: https://www.instagram.com/username/
            // Direct message is opened in /direct/inbox/ or direct message url
            window.open(lead.instagram, '_blank');
        }, 800);
    },

    // ---- Search ----
    async handleSearch() {
        const query = UI.el.queryInput.value.trim();
        const city = UI.el.cityInput.value.trim();
        const maxResults = parseInt(UI.el.maxResultsSelect.value) || 20;
        const includeWithWebsite = UI.el.includeWebsiteToggle?.checked || false;

        if (!query) {
            UI.showToast('Please enter a business type (e.g., gym, salon)', 'error');
            UI.el.queryInput.focus();
            return;
        }

        if (!city) {
            UI.showToast('Please enter a city name (e.g., Bhopal, Delhi)', 'error');
            UI.el.cityInput.focus();
            return;
        }

        if (!AppState.hasApiKey) {
            UI.showToast('Please configure your SerpApi key first', 'error');
            UI.openModal('settingsModal');
            return;
        }

        try {
            const hideSaved = UI.el.hideSavedLeadsToggle?.checked || false;
            const deepScan = UI.el.deepScanToggle?.checked || false;
            const zonesText = UI.el.deepScanZonesInput?.value || "";
            const zones = zonesText.split(',').map(z => z.trim()).filter(Boolean);

            UI.showLoading(`Searching for "${query}" in ${city}...`);
            
            // Save search params for pagination
            AppState.activeSearchParams = {
                query,
                city,
                maxResults,
                includeWithWebsite,
                hideSaved,
                deepScan,
                zones
            };
            AppState.currentOffset = 0; // Reset offset

            const data = await API.search(query, city, maxResults, includeWithWebsite, hideSaved, deepScan, zones, 0);
            
            AppState.leads = data.leads;
            AppState.allResults = data.all_results;
            AppState.stats = data.stats;
            
            UI.updateStats(data.stats);
            UI.renderLeads(data.leads);
            
            UI.el.resultsTitle.textContent = `Results for "${data.query}"`;
            
            // Scroll to results
            setTimeout(() => {
                UI.el.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 300);
            
            UI.showToast(`Found ${data.stats.leads_count} leads out of ${data.stats.total_found} businesses`, 'success');
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async loadMoreLeads() {
        const params = AppState.activeSearchParams;
        if (!params) return;

        try {
            // Disable Load More button during request
            if (UI.el.loadMoreBtn) {
                UI.el.loadMoreBtn.disabled = true;
                UI.el.loadMoreBtn.innerHTML = '⏳ Loading Next Page...';
            }

            // Increment currentOffset by the max results we requested previously
            AppState.currentOffset += params.maxResults;

            UI.showLoading(`Loading page offset starting at ${AppState.currentOffset}...`);

            const data = await API.search(
                params.query,
                params.city,
                params.maxResults,
                params.includeWithWebsite,
                params.hideSaved,
                params.deepScan,
                params.zones,
                AppState.currentOffset
            );

            if (data.leads && data.leads.length > 0) {
                // Append new leads
                AppState.leads = AppState.leads.concat(data.leads);
                AppState.allResults = AppState.allResults.concat(data.all_results);
                
                // Accumulate stats across pages instead of overwriting (BUG #15 fix)
                const pageStats = data.stats;
                AppState.stats.total_found = (AppState.stats.total_found || 0) + (pageStats.total_found || 0);
                AppState.stats.leads_count = (AppState.stats.leads_count || 0) + (pageStats.leads_count || 0);
                AppState.stats.broken_websites = (AppState.stats.broken_websites || 0) + (pageStats.broken_websites || 0);
                AppState.stats.high_priority = (AppState.stats.high_priority || 0) + (pageStats.high_priority || 0);
                AppState.stats.medium_priority = (AppState.stats.medium_priority || 0) + (pageStats.medium_priority || 0);
                AppState.stats.with_phone = (AppState.stats.with_phone || 0) + (pageStats.with_phone || 0);
                AppState.stats.with_whatsapp = (AppState.stats.with_whatsapp || 0) + (pageStats.with_whatsapp || 0);
                UI.updateStats(AppState.stats);
                
                // Re-render
                UI.renderLeads(AppState.leads);
                
                UI.showToast(`Loaded ${pageStats.leads_count} more leads! Total leads in view: ${AppState.leads.length}`, 'success');
            } else {
                UI.showToast('No more new leads found on the next pages.', 'info');
                if (UI.el.loadMoreContainer) {
                    UI.el.loadMoreContainer.style.display = 'none';
                }
            }
        } catch (error) {
            UI.showToast(error.message, 'error');
            // Re-enable
            if (UI.el.loadMoreBtn) {
                UI.el.loadMoreBtn.disabled = false;
                UI.el.loadMoreBtn.innerHTML = '⏭️ Load Next Page (Get More Leads)';
            }
        } finally {
            UI.hideLoading();
            if (UI.el.loadMoreBtn) {
                UI.el.loadMoreBtn.disabled = false;
                UI.el.loadMoreBtn.innerHTML = '⏭️ Load Next Page (Get More Leads)';
            }
        }
    },

    // ---- Kanban Views ----
    switchView(view) {
        AppState.currentView = view;
        
        if (view === 'kanban') {
            UI.el.listViewBtn?.classList.remove('active');
            UI.el.kanbanViewBtn?.classList.add('active');
        } else {
            UI.el.listViewBtn?.classList.add('active');
            UI.el.kanbanViewBtn?.classList.remove('active');
        }
        
        UI.renderLeads(AppState.leads);
    },

    // ---- WhatsApp ----
    async loadTemplates() {
        try {
            const data = await API.getTemplates();
            AppState.whatsappTemplates = data.templates;
            this.renderTemplateOptions();
        } catch (error) {
            console.error('Failed to load templates:', error);
        }
    },

    renderTemplateOptions() {
        const container = UI.el.templateOptions;
        if (!container) return;
        
        container.innerHTML = Object.entries(AppState.whatsappTemplates)
            .filter(([key]) => key !== 'custom')
            .map(([key, template], i) => `
                <label class="template-option ${i === 0 ? 'selected' : ''}">
                    <input type="radio" name="template" value="${key}" ${i === 0 ? 'checked' : ''}>
                    <div>
                        <div class="template-name">${template.name}</div>
                    </div>
                </label>
            `).join('') + `
                <label class="template-option">
                    <input type="radio" name="template" value="custom">
                    <div>
                        <div class="template-name">✏️ Custom Message</div>
                    </div>
                </label>
            `;

    },

    openWhatsApp(indexOrLead) {
        const lead = typeof indexOrLead === 'object' ? indexOrLead : AppState.leads[indexOrLead];
        if (!lead || !lead.whatsapp_number) {
            UI.showToast('No WhatsApp number available for this business', 'error');
            return;
        }
        
        AppState.currentWhatsAppLead = lead;
        
        // Update modal header with business name
        document.getElementById('whatsappBusinessName').textContent = lead.name;
        document.getElementById('whatsappPhoneNumber').textContent = lead.phone || lead.whatsapp_number;
        
        // Check if custom_pitch is already available for this lead
        const customMessageInput = document.getElementById('customMessageInput');
        const customArea = document.getElementById('customMessageArea');
        
        if (lead.custom_pitch) {
            if (customMessageInput) {
                customMessageInput.value = lead.custom_pitch;
            }
            if (customArea) {
                customArea.style.display = 'block';
            }
            
            // Programmatically select "custom" template
            setTimeout(() => {
                const customRadio = document.querySelector('input[name="template"][value="custom"]');
                if (customRadio) {
                    customRadio.checked = true;
                    AppState.selectedTemplate = 'custom';
                    
                    const container = UI.el.templateOptions;
                    if (container) {
                        container.querySelectorAll('.template-option').forEach(o => o.classList.remove('selected'));
                        customRadio.closest('.template-option')?.classList.add('selected');
                    }
                    this.updateMessagePreview();
                }
            }, 50);
            UI.showToast('✨ Custom AI Pitch preloaded from database!', 'success');
        } else {
            // Reset to default
            if (customMessageInput) {
                customMessageInput.value = '';
            }
            if (customArea) {
                customArea.style.display = 'none';
            }
            
            // Re-select first template
            setTimeout(() => {
                const firstRadio = document.querySelector('input[name="template"]');
                if (firstRadio) {
                    firstRadio.checked = true;
                    AppState.selectedTemplate = firstRadio.value;
                    
                    const container = UI.el.templateOptions;
                    if (container) {
                        container.querySelectorAll('.template-option').forEach(o => o.classList.remove('selected'));
                        firstRadio.closest('.template-option')?.classList.add('selected');
                    }
                    this.updateMessagePreview();
                }
            }, 50);
        }
        
        this.updateMessagePreview();
        UI.openModal('whatsappModal');
    },

    updateMessagePreview() {
        const lead = AppState.currentWhatsAppLead;
        if (!lead) return;
        
        const template = AppState.selectedTemplate;
        let message = '';
        
        if (template === 'custom') {
            message = document.getElementById('customMessageInput')?.value || '';
        } else {
            const templateData = AppState.whatsappTemplates[template];
            if (templateData) {
                message = templateData.message;
            }
        }
        
        // Replace template variables
        const projectSampleText = this.getBestPortfolioProjectSample(lead);
        message = message
            .replace(/\{business_name\}/g, lead.name || 'there')
            .replace(/\{city\}/g, lead.city || 'your city')
            .replace(/\{category\}/g, lead.category || 'business')
            .replace(/\{rating\}/g, lead.rating || 'great')
            .replace(/\{reviews\}/g, (lead.reviews !== undefined && lead.reviews !== null) ? lead.reviews : 'many')
            .replace(/\{address\}/g, lead.address || '')
            .replace(/\{phone\}/g, lead.phone || '')
            .replace(/\{project_sample\}/g, projectSampleText);
        
        const preview = document.getElementById('messagePreview');
        if (preview) {
            preview.textContent = message || 'Type your message above...';
        }
    },

    getBestPortfolioProjectSample(lead) {
        const portfolioUrl = localStorage.getItem('portfolio_url');
        const projectsStr = localStorage.getItem('portfolio_projects');
        
        if (!portfolioUrl) {
            return "hamare work samples hamare portfolio par dekh sakte hain: https://raunaksharmaq64.github.io/portfolio/";
        }
        
        let projects = [];
        try {
            if (projectsStr) {
                projects = JSON.parse(projectsStr);
            }
        } catch (e) {
            console.error('Error parsing portfolio projects', e);
        }
        
        if (!projects || projects.length === 0) {
            return `hamare work samples hamare portfolio par dekh sakte hain: ${portfolioUrl}`;
        }
        
        const category = (lead.category || '').toLowerCase();
        const name = (lead.name || '').toLowerCase();
        
        // 1. Gym / Fitness matching
        if (category.includes('gym') || category.includes('fitness') || category.includes('workout') || category.includes('health') || 
            name.includes('gym') || name.includes('fitness') || name.includes('workout')) {
            const match = projects.find(p => p.title.toLowerCase().includes('gym') || p.desc.toLowerCase().includes('gym'));
            if (match && match.demo_url) {
                return `maine haal hi mein ek GYM website banayi hai, aap is link par demo dekh sakte hain: ${match.demo_url}`;
            }
        }
        
        // 2. Hotel / Restaurant / Cafe / Food matching
        if (category.includes('hotel') || category.includes('restaurant') || category.includes('cafe') || category.includes('food') || category.includes('dine') || category.includes('bakery') || category.includes('sweet') ||
            name.includes('hotel') || name.includes('restaurant') || name.includes('cafe') || name.includes('food') || name.includes('dine') || name.includes('bakery')) {
            const match = projects.find(p => p.title.toLowerCase().includes('hotel') || p.title.toLowerCase().includes('restaurant') || p.title.toLowerCase().includes('prandium') || p.desc.toLowerCase().includes('hotel') || p.desc.toLowerCase().includes('restaurant'));
            if (match && match.demo_url) {
                return `maine haal hi mein ek Hotel/Restaurant website banayi hai, aap is link par demo dekh sakte hain: ${match.demo_url}`;
            }
        }
        
        // 3. Hostel / Student PG matching
        if (category.includes('hostel') || category.includes('pg') || category.includes('stay') || category.includes('accommodation') ||
            name.includes('hostel') || name.includes('pg') || name.includes('stay') || name.includes('accommodation')) {
            const match = projects.find(p => p.title.toLowerCase().includes('hostel') || p.title.toLowerCase().includes('buddy'));
            if (match && match.demo_url) {
                return `maine haal hi mein ek Hostel discovery platform banaya hai, aap is link par demo dekh sakte hain: ${match.demo_url}`;
            }
        }
        
        // 4. Default Fallback to main portfolio
        return `hamare work samples hamare portfolio par dekh sakte hain: ${portfolioUrl}`;
    },
 
    async sendWhatsApp() {
        const lead = AppState.currentWhatsAppLead;
        if (!lead) return;
        
        // Disable button to prevent double clicks
        const btn = document.getElementById('sendWhatsAppBtn');
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Generating...';
        btn.disabled = true;
        
        try {
            // Fetch the fully-rendered preview text so we capture the exact matching portfolio URL
            const previewMessage = document.getElementById('messagePreview')?.textContent || '';
            
            const data = await API.generateWhatsAppLink(
                lead.whatsapp_number,
                'custom', // Force the backend to use the exact message we resolved
                lead,
                previewMessage
            );
            
            if (data.whatsapp_link) {
                // Use location.href or hidden <a> to avoid popup blocker
                const a = document.createElement('a');
                a.href = data.whatsapp_link;
                a.target = '_blank';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                UI.closeModal('whatsappModal');
                UI.showToast(`WhatsApp opened for ${lead.name}`, 'success');
                
                // Automatically mark lead as contacted and transition pipeline to PITCHED
                try {
                    lead.contacted = 1;
                    lead.contact_date = new Date().toISOString();
                    lead.pipeline_stage = 'PITCHED';
                    
                    // Guard: Only sync to backend if lead has a database ID (BUG #10 fix)
                    if (lead.id) {
                        await API.request(`/api/leads/${lead.id}/contact`, {
                            method: 'POST',
                            body: JSON.stringify({ notes: lead.notes || 'Contacted via WhatsApp' })
                        });
                    }
                    
                    UI.renderLeads(AppState.leads);
                    
                    // Trigger follow-up scheduler (only if lead has DB ID)
                    if (lead.id) {
                        setTimeout(() => {
                            App.promptFollowupReminder(lead.id, lead.name);
                        }, 500);
                    }
                } catch (contactErr) {
                    console.error('Error marking contacted:', contactErr);
                }
            }
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    },

    // ---- Copy Phone ----
    copyPhone(index) {
        const lead = AppState.leads[index];
        if (!lead || !lead.phone) {
            UI.showToast('No phone number available', 'error');
            return;
        }
        
        navigator.clipboard.writeText(lead.phone).then(() => {
            UI.showToast(`Copied: ${lead.phone}`, 'success');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = lead.phone;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            UI.showToast(`Copied: ${lead.phone}`, 'success');
        });
    },

    // ---- Copy Mockup Link ----
    copyMockupLink(id) {
        if (!id) {
            UI.showToast('Lead must be saved to database to generate mockup', 'error');
            return;
        }
        
        const senderName = localStorage.getItem('sender_name') || '';
        const senderBrand = localStorage.getItem('sender_brand') || '';
        
        const url = `${window.location.origin}/preview/${id}?sender_name=${encodeURIComponent(senderName)}&sender_brand=${encodeURIComponent(senderBrand)}`;
        
        navigator.clipboard.writeText(url).then(() => {
            UI.showToast('🚀 Mockup Link copied to clipboard! Ready to share!', 'success');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = url;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            UI.showToast('🚀 Mockup Link copied to clipboard! Ready to share!', 'success');
        });
    },

    // ---- Export ----
    async exportExcel() {
        if (AppState.leads.length === 0) {
            UI.showToast('No leads to export', 'error');
            return;
        }
        
        try {
            UI.showToast('Generating Excel file...', 'info');
            const blob = await API.exportExcel(AppState.leads);
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `leads_${new Date().toISOString().slice(0, 10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            
            UI.showToast(`Exported ${AppState.leads.length} leads to Excel`, 'success');
        } catch (error) {
            UI.showToast('Export failed: ' + error.message, 'error');
        }
    },

    // ---- History ----
    async loadHistory() {
        try {
            const data = await API.getHistory();
            const container = document.getElementById('historyList');
            
            if (data.history && data.history.length > 0) {
                // Store history data for safe re-run (BUG #7/#8 fix: no inline onclick with unescaped strings)
                AppState.searchHistory = data.history;

                container.innerHTML = data.history.map((item, idx) => `
                    <div class="history-item" data-history-index="${idx}">
                        <div>
                            <div class="history-query">🔍 ${UI.escapeHtml(item.query)} in ${UI.escapeHtml(item.city)}</div>
                        </div>
                        <div class="history-meta">
                            <span>📊 ${item.results_count} found</span>
                            <span>🎯 ${item.leads_count} leads</span>
                            <span>📅 ${new Date(item.searched_at).toLocaleDateString()}</span>
                        </div>
                    </div>
                `).join('');

                // Event delegation: attach click handlers via data-attribute (safe from XSS/quotes)
                container.querySelectorAll('.history-item[data-history-index]').forEach(el => {
                    el.addEventListener('click', () => {
                        const idx = parseInt(el.getAttribute('data-history-index'));
                        const item = AppState.searchHistory[idx];
                        if (item) {
                            App.rerunSearch(item.query, item.city);
                        }
                    });
                });
            } else {
                container.innerHTML = `
                    <div class="empty-state" style="padding: 32px;">
                        <div class="empty-state-icon">📜</div>
                        <div class="empty-state-title">No search history yet</div>
                        <div class="empty-state-text">Your searches will appear here</div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    },

    async handleBulkScanSocials() {
        if (AppState.leads.length === 0) {
            UI.showToast('Bulk scan ke liye table mein leads hona zaroori hai!', 'error');
            return;
        }

        const serpKey = localStorage.getItem('serpapi_key') || '';
        
        // Disable bulk buttons
        UI.el.bulkScanSocialsBtn.disabled = true;
        
        // Show progress banner
        UI.el.bulkProgressBanner.style.display = 'block';
        UI.el.bulkProgressLabel.textContent = 'Preparing bulk social scan...';
        UI.el.bulkProgressPercentage.textContent = '0%';
        UI.el.bulkProgressBar.style.width = '0%';

        const leadsToScan = AppState.leads.filter(l => !l.instagram && !l.facebook);
        if (leadsToScan.length === 0) {
            UI.showToast('Sabhi leads ke socials already scanned hain!', 'info');
            UI.el.bulkScanSocialsBtn.disabled = false;
            UI.el.bulkProgressBanner.style.display = 'none';
            return;
        }

        let completed = 0;
        const total = leadsToScan.length;

        for (const lead of leadsToScan) {
            try {
                // Find row index in AppState.leads
                const idx = AppState.leads.findIndex(l => l.id === lead.id);
                if (idx === -1) continue;

                // Show spinner in UI row (add active scanning indicator)
                const socialCell = document.querySelector(`#leadsTableBody tr:nth-child(${idx + 1}) td:nth-child(9)`);
                if (socialCell) {
                    socialCell.innerHTML = '<span style="font-size: 0.85rem; color: var(--accent-cyan); animation: pulse 1s infinite;">⏳ Scanning...</span>';
                }

                UI.el.bulkProgressLabel.textContent = `Scanning socials for "${lead.name}" (${completed + 1}/${total})...`;

                const data = await API.request(`/api/leads/${lead.id}/scan-socials`, {
                    method: 'POST'
                });

                if (data.success) {
                    // Update model state
                    lead.instagram = data.instagram;
                    lead.facebook = data.facebook;

                    // Update UI row
                    if (socialCell) {
                        let links = [];
                        if (data.instagram) {
                            links.push(`<a href="${data.instagram}" target="_blank" class="social-icon instagram" title="Instagram">📸</a>`);
                        }
                        if (data.facebook) {
                            links.push(`<a href="${data.facebook}" target="_blank" class="social-icon facebook" title="Facebook">👥</a>`);
                        }
                        socialCell.innerHTML = links.length > 0 ? links.join(' ') : '<span style="color: var(--text-secondary); font-size: 0.85rem;">✗ Not found</span>';
                    }
                } else {
                    if (socialCell) {
                        socialCell.innerHTML = '<span style="color: var(--accent-red); font-size: 0.85rem;">✗ Error</span>';
                    }
                }
            } catch (err) {
                console.error(`Error scanning lead ${lead.id} socials:`, err);
            }

            completed++;
            const pct = Math.round((completed / total) * 100);
            UI.el.bulkProgressPercentage.textContent = `${pct}%`;
            UI.el.bulkProgressBar.style.width = `${pct}%`;
        }

        UI.showToast(`🎉 Bulk social scan completed! Scanned ${total} leads.`, 'success');
        UI.el.bulkProgressLabel.textContent = 'Bulk scan complete!';
        
        setTimeout(() => {
            UI.el.bulkProgressBanner.style.display = 'none';
            UI.el.bulkScanSocialsBtn.disabled = false;
        }, 3000);
    },



    rerunSearch(query, city) {
        UI.el.queryInput.value = query;
        UI.el.cityInput.value = city;
        UI.closeModal('historyModal');
        this.handleSearch();
    },

    checkSmtpConfig() {
        const host = localStorage.getItem('smtp_host') || '';
        const port = localStorage.getItem('smtp_port') || '';
        const email = localStorage.getItem('smtp_email') || '';
        const password = localStorage.getItem('smtp_password') || '';
        const useSSL = localStorage.getItem('smtp_use_ssl') !== 'false';

        if (UI.el.smtpHostInput) UI.el.smtpHostInput.value = host;
        if (UI.el.smtpPortInput) UI.el.smtpPortInput.value = port;
        if (UI.el.smtpEmailInput) UI.el.smtpEmailInput.value = email;
        if (UI.el.smtpPasswordInput) UI.el.smtpPasswordInput.value = password;
        if (UI.el.smtpUseSSL) UI.el.smtpUseSSL.checked = useSSL;

        const statusEl = UI.el.smtpStatus;
        if (statusEl) {
            if (host && port && email && password) {
                statusEl.className = 'api-key-status active';
                statusEl.textContent = '✓ Configured';
            } else {
                statusEl.className = 'api-key-status inactive';
                statusEl.textContent = '✗ Not Set';
            }
        }
    },

    saveSmtpSettings() {
        const host = UI.el.smtpHostInput?.value.trim() || '';
        const port = UI.el.smtpPortInput?.value.trim() || '';
        const email = UI.el.smtpEmailInput?.value.trim() || '';
        const password = UI.el.smtpPasswordInput?.value.trim() || '';
        const useSSL = UI.el.smtpUseSSL ? UI.el.smtpUseSSL.checked : true;

        if (!host || !port || !email || !password) {
            UI.showToast('Please fill in all SMTP fields before saving.', 'warning');
            return;
        }

        localStorage.setItem('smtp_host', host);
        localStorage.setItem('smtp_port', port);
        localStorage.setItem('smtp_email', email);
        localStorage.setItem('smtp_password', password);
        localStorage.setItem('smtp_use_ssl', useSSL ? 'true' : 'false');

        this.checkSmtpConfig();
        UI.showToast('SMTP credentials saved securely to your browser!', 'success');
    },

    async scanEmail(leadId, index) {
        const tableBtn = document.getElementById(`scanEmailBtn-${index}`);
        const kanbanBtn = document.getElementById(`kanbanScanEmailBtn-${index}`);
        
        if (tableBtn) {
            tableBtn.innerHTML = '⏳ Scanning...';
            tableBtn.disabled = true;
        }
        if (kanbanBtn) {
            kanbanBtn.innerHTML = '⏳ Scanning...';
            kanbanBtn.disabled = true;
        }

        try {
            const data = await API.request(`/api/leads/${leadId}/scan-email`, {
                method: 'POST'
            });

            if (data.success && data.email) {
                // Find lead by ID instead of array index to handle stale indices after sort (BUG #9 fix)
                const safeIdx = AppState.leads.findIndex(l => l.id === leadId);
                if (safeIdx !== -1) {
                    AppState.leads[safeIdx].email = data.email;
                }
                UI.showToast(`📧 Found public email: ${data.email}!`, 'success');
                UI.renderLeads(AppState.leads);
            } else {
                UI.showToast(data.message || 'No public email found for this website.', 'info');
                if (tableBtn) {
                    tableBtn.innerHTML = '🔍📧';
                    tableBtn.disabled = false;
                }
                if (kanbanBtn) {
                    kanbanBtn.innerHTML = '🔍 Email';
                    kanbanBtn.disabled = false;
                }
            }
        } catch (error) {
            UI.showToast('Email scan failed: ' + error.message, 'error');
            if (tableBtn) {
                tableBtn.innerHTML = '🔍📧';
                tableBtn.disabled = false;
            }
            if (kanbanBtn) {
                kanbanBtn.innerHTML = '🔍 Email';
                kanbanBtn.disabled = false;
            }
        }
    },

    openEmail(indexOrLead) {
        const lead = typeof indexOrLead === 'object' ? indexOrLead : AppState.leads[indexOrLead];
        if (!lead) return;

        const index = typeof indexOrLead === 'number' ? indexOrLead : AppState.leads.findIndex(l => l.id === lead.id);
        AppState.currentEmailIndex = index;
        AppState.currentEmailLead = lead;

        if (UI.el.emailBusinessName) UI.el.emailBusinessName.textContent = lead.name;
        
        if (UI.el.emailSubjectInput) UI.el.emailSubjectInput.value = '';
        if (UI.el.emailBodyInput) UI.el.emailBodyInput.value = '';

        const addressText = document.getElementById('emailAddressText');
        const scanBtn = UI.el.scanEmailOnDemandBtn;

        if (lead.email) {
            if (addressText) {
                addressText.textContent = lead.email;
                addressText.style.color = 'var(--accent-cyan)';
            }
            if (scanBtn) scanBtn.style.display = 'none';
        } else {
            if (addressText) {
                addressText.textContent = 'No email scanned yet.';
                addressText.style.color = 'var(--accent-red)';
            }
            if (scanBtn) {
                scanBtn.style.display = 'inline-block';
                scanBtn.innerHTML = '🔍 Scan Website';
                scanBtn.disabled = false;
            }
        }

        UI.openModal('emailModal');
    },

    async scanEmailOnDemand() {
        const lead = AppState.currentEmailLead;
        const index = AppState.currentEmailIndex;
        if (!lead) return;

        const scanBtn = UI.el.scanEmailOnDemandBtn;
        const addressText = document.getElementById('emailAddressText');

        if (scanBtn) {
            scanBtn.innerHTML = '⏳ Scanning...';
            scanBtn.disabled = true;
        }
        if (addressText) {
            addressText.textContent = 'Deep crawling website for contact emails...';
            addressText.style.color = 'var(--accent-cyan)';
        }

        try {
            const data = await API.request(`/api/leads/${lead.id}/scan-email`, {
                method: 'POST'
            });

            if (data.success && data.email) {
                lead.email = data.email;
                AppState.leads[index].email = data.email;
                
                if (addressText) {
                    addressText.textContent = data.email;
                    addressText.style.color = 'var(--accent-cyan)';
                }
                if (scanBtn) scanBtn.style.display = 'none';
                
                UI.showToast(`📧 Successfully extracted: ${data.email}!`, 'success');
                UI.renderLeads(AppState.leads);
            } else {
                UI.showToast('No public email addresses could be discovered.', 'info');
                if (addressText) {
                    addressText.textContent = 'Scanned: No emails found.';
                    addressText.style.color = 'var(--accent-red)';
                }
                if (scanBtn) {
                    scanBtn.innerHTML = '🔍 Scan Website';
                    scanBtn.disabled = false;
                }
            }
        } catch (error) {
            UI.showToast('Scanning failed: ' + error.message, 'error');
            if (addressText) {
                addressText.textContent = 'Scan error. Please try again.';
                addressText.style.color = 'var(--accent-red)';
            }
            if (scanBtn) {
                scanBtn.innerHTML = '🔍 Scan Website';
                scanBtn.disabled = false;
            }
        }
    },

    async generateAIEmail() {
        const lead = AppState.currentEmailLead;
        if (!lead) return;

        const geminiKey = localStorage.getItem('gemini_api_key');
        if (!geminiKey) {
            UI.showToast('Please configure your Gemini API Key in Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const projectSample = this.getBestPortfolioProjectSample(lead);
        const tone = UI.el.emailToneSelect?.value || 'elite';

        try {
            UI.showLoading('AI Writer compiling professional email...');
            
            const data = await API.request('/api/outreach/generate-email-ai', {
                method: 'POST',
                headers: {
                    'X-Gemini-API-Key': geminiKey
                },
                body: JSON.stringify({
                    lead: lead,
                    project_sample: projectSample,
                    tone: tone,
                    sender: {
                        name: localStorage.getItem('sender_name') || '',
                        brand: localStorage.getItem('sender_brand') || '',
                        role: localStorage.getItem('sender_role') || ''
                    },
                    custom_pitch_rules: localStorage.getItem('custom_pitch_rules') || ''
                })
            });

            if (data.success) {
                if (UI.el.emailSubjectInput) UI.el.emailSubjectInput.value = data.subject || '';
                if (UI.el.emailBodyInput) UI.el.emailBodyInput.value = data.body || '';
                UI.showToast('✨ High-converting AI cold email generated!', 'success');
            } else {
                UI.showToast(data.error || 'Failed to generate email pitch.', 'error');
            }
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    openMailClient() {
        const lead = AppState.currentEmailLead;
        if (!lead) return;

        const toEmail = lead.email || '';
        const subject = UI.el.emailSubjectInput?.value.trim() || '';
        const body = UI.el.emailBodyInput?.value.trim() || '';

        if (!toEmail) {
            UI.showToast('Recipient email is missing! Try scanning the website first.', 'warning');
            return;
        }
        if (!subject || !body) {
            UI.showToast('Please type or generate a subject and body first!', 'warning');
            return;
        }

        const mailtoUrl = `mailto:${encodeURIComponent(toEmail)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
        
        const a = document.createElement('a');
        a.href = mailtoUrl;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        UI.closeModal('emailModal');
        UI.showToast('Native mail client opened!', 'success');
        
        this.markLeadPitched(lead);
    },

    async sendSMTPEmail() {
        const lead = AppState.currentEmailLead;
        if (!lead) return;

        const toEmail = lead.email || '';
        const subject = UI.el.emailSubjectInput?.value.trim() || '';
        const body = UI.el.emailBodyInput?.value.trim() || '';

        if (!toEmail) {
            UI.showToast('Recipient email is missing! Try scanning the website first.', 'warning');
            return;
        }
        if (!subject || !body) {
            UI.showToast('Please type or generate a subject and body first!', 'warning');
            return;
        }

        const host = localStorage.getItem('smtp_host') || '';
        const port = localStorage.getItem('smtp_port') || '';
        const email = localStorage.getItem('smtp_email') || '';
        const password = localStorage.getItem('smtp_password') || '';
        const useSSL = localStorage.getItem('smtp_use_ssl') === 'true';

        if (!host || !port || !email || !password) {
            UI.showToast('Direct dispatch is disabled. Configure your SMTP Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        try {
            UI.showLoading('Connecting to SMTP server and sending mail...');
            
            const data = await API.request('/api/outreach/send-smtp-email', {
                method: 'POST',
                body: JSON.stringify({
                    to_email: toEmail,
                    subject: subject,
                    body: body,
                    lead_id: lead.id,
                    smtp_config: {
                        host: host,
                        port: parseInt(port),
                        email: email,
                        password: password,
                        use_ssl: useSSL
                    }
                })
            });

            if (data.success) {
                UI.showToast(data.message || 'Email successfully sent!', 'success');
                UI.closeModal('emailModal');
                
                this.markLeadPitched(lead);
            } else {
                UI.showToast(data.error || 'Direct dispatch failed.', 'error');
            }
        } catch (error) {
            UI.showToast('SMTP Direct Send failed: ' + error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async markLeadPitched(lead) {
        const index = AppState.leads.findIndex(l => l.id === lead.id);
        if (index === -1) return;

        try {
            AppState.leads[index].contacted = 1;
            AppState.leads[index].contact_date = new Date().toISOString();
            AppState.leads[index].pipeline_stage = 'PITCHED';
            
            UI.renderLeads(AppState.leads);
            
            // Trigger follow-up scheduler
            setTimeout(() => {
                App.promptFollowupReminder(lead.id, lead.name);
            }, 500);
            
            await API.request(`/api/leads/${lead.id}/contact`, {
                method: 'POST',
                body: JSON.stringify({ notes: 'Contacted via Cold Email' })
            });
            await API.updateLeadPipelineStage(lead.id, 'PITCHED');
        } catch (err) {
            console.error('Error syncing pipeline stage to Pitched:', err);
        }
    },

    async loadReminders() {
        try {
            const data = await API.request('/api/reminders');
            if (data.success && data.reminders) {
                AppState.reminders = data.reminders;
                
                // Count due/overdue reminders
                const todayStr = new Date().toISOString().split('T')[0];
                const dueReminders = data.reminders.filter(r => r.remind_date <= todayStr);
                const count = dueReminders.length;
                
                const banner = UI.el.followupRemindersBanner;
                const textEl = UI.el.followupRemindersText;
                
                if (count > 0 && banner && textEl) {
                    textEl.textContent = `You have ${count} pending follow-up reminder${count > 1 ? 's' : ''} due today or overdue.`;
                    banner.style.display = 'block';
                } else if (banner) {
                    banner.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error loading reminders:', error);
        }
    },

    promptFollowupReminder(leadId, leadName) {
        AppState.currentReminderLeadId = leadId;
        
        if (UI.el.reminderLeadName) {
            UI.el.reminderLeadName.textContent = leadName;
        }
        if (UI.el.customReminderDateInput) {
            UI.el.customReminderDateInput.value = '';
        }
        
        // Reset preset buttons styling
        document.querySelectorAll('.reminder-preset-btn').forEach(btn => {
            btn.classList.remove('selected');
            btn.style.borderColor = '';
            btn.style.color = '';
            btn.style.background = '';
            
            // Set 3 days as default
            if (btn.getAttribute('data-days') === '3') {
                btn.classList.add('selected');
                btn.style.borderColor = 'var(--accent-orange)';
                btn.style.color = 'var(--accent-orange)';
                btn.style.background = 'rgba(249, 115, 22, 0.05)';
            }
        });
        
        UI.openModal('scheduleReminderModal');
    },

    async saveScheduledReminder() {
        const leadId = AppState.currentReminderLeadId;
        if (!leadId) return;
        
        const customDate = UI.el.customReminderDateInput?.value || '';
        let payload = {};
        
        if (customDate) {
            payload = { custom_date: customDate };
        } else {
            const selectedPreset = document.querySelector('.reminder-preset-btn.selected');
            const days = selectedPreset ? parseInt(selectedPreset.getAttribute('data-days')) : 3;
            payload = { days: days };
        }
        
        try {
            UI.showLoading('Saving follow-up reminder...');
            const data = await API.request(`/api/leads/${leadId}/schedule-reminder`, {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            
            if (data.success) {
                UI.showToast('📅 Reminder scheduled successfully!', 'success');
                UI.closeModal('scheduleReminderModal');
                this.loadReminders();
            } else {
                UI.showToast(data.error || 'Failed to save reminder.', 'error');
            }
        } catch (error) {
            UI.showToast('Failed to save reminder: ' + error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    openActiveReminders() {
        this.renderFollowups();
        UI.openModal('followupsModal');
    },

    async dismissLeadReminder(leadId) {
        try {
            UI.showLoading('Dismissing reminder...');
            const data = await API.request(`/api/leads/${leadId}/dismiss-reminder`, {
                method: 'POST'
            });
            if (data.success) {
                UI.showToast('Reminder cleared successfully!', 'success');
                await this.loadReminders();
                this.renderFollowups();
            } else {
                UI.showToast(data.error || 'Failed to clear reminder.', 'error');
            }
        } catch (error) {
            UI.showToast('Error clearing reminder: ' + error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    renderFollowups() {
        const container = UI.el.followupsListContainer;
        if (!container) return;
        
        const reminders = AppState.reminders || [];
        if (reminders.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="padding: 24px;">
                    <div class="empty-state-icon">⏰</div>
                    <div class="empty-state-title">No pending follow-ups!</div>
                    <div class="empty-state-desc">You are all caught up on your sales outreach. Great job!</div>
                </div>
            `;
            return;
        }
        
        const todayStr = new Date().toISOString().split('T')[0];
        const today = new Date(todayStr);
        
        let html = '';
        reminders.forEach(lead => {
            const remindDate = new Date(lead.remind_date);
            const diffTime = remindDate - today;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            
            let dateBadge = '';
            if (diffDays === 0) {
                dateBadge = `<span style="font-size: 0.75rem; color: var(--accent-orange); font-weight: 700; background: rgba(249, 115, 22, 0.1); padding: 2px 6px; border-radius: 4px;">⏰ Due Today</span>`;
            } else if (diffDays < 0) {
                const absDays = Math.abs(diffDays);
                dateBadge = `<span style="font-size: 0.75rem; color: var(--accent-red); font-weight: 700; background: rgba(239, 68, 68, 0.1); padding: 2px 6px; border-radius: 4px;">⚠️ Overdue by ${absDays} day${absDays > 1 ? 's' : ''}</span>`;
            } else {
                dateBadge = `<span style="font-size: 0.75rem; color: var(--accent-cyan); font-weight: 700; background: rgba(0, 240, 255, 0.1); padding: 2px 6px; border-radius: 4px;">📅 Due in ${diffDays} day${diffDays > 1 ? 's' : ''}</span>`;
            }
            
            // Build action buttons safely
            let whatsappBtn = '';
            if (lead.whatsapp_number) {
                whatsappBtn = `<button class="row-btn whatsapp" data-tooltip="WhatsApp Pitch" onclick="App.triggerWhatsAppReminder(${lead.id})" style="padding: 6px; border-radius: 4px;">💬</button>`;
            }
            
            let emailBtn = '';
            if (lead.email) {
                emailBtn = `<button class="row-btn email" data-tooltip="Email Pitch" onclick="App.triggerEmailReminder(${lead.id})" style="padding: 6px; border-radius: 4px;">📧</button>`;
            }
            
            html += `
                <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; gap: 12px;">
                    <div>
                        <div style="font-weight: 700; font-size: 0.95rem; color: var(--text-primary);">${lead.name}</div>
                        <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px;">
                            ${lead.category} • ${lead.city}
                        </div>
                        <div style="margin-top: 6px; display: flex; align-items: center; gap: 6px;">
                            ${dateBadge}
                            <span style="font-size: 0.7rem; color: var(--text-muted);">(${lead.remind_date})</span>
                        </div>
                    </div>
                    <div style="display: flex; gap: 6px;">
                        ${whatsappBtn}
                        ${emailBtn}
                        <button class="row-btn delete" data-tooltip="Dismiss Reminder" onclick="App.dismissLeadReminder(${lead.id})" style="border-color: var(--accent-green); color: var(--accent-green); background: rgba(16, 185, 129, 0.05); padding: 6px; border-radius: 4px;">✓</button>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    },

    triggerWhatsAppReminder(leadId) {
        const lead = (AppState.reminders || []).find(r => r.id === leadId);
        if (!lead) return;
        
        UI.closeModal('followupsModal');
        setTimeout(() => {
            this.openWhatsApp(lead);
        }, 300);
    },

    triggerEmailReminder(leadId) {
        const lead = (AppState.reminders || []).find(r => r.id === leadId);
        if (!lead) return;
        
        UI.closeModal('followupsModal');
        setTimeout(() => {
            this.openEmail(lead);
        }, 300);
    },

    // ============================================================
    // Bulk Email Campaign Center Logic & Outbox
    // ============================================================
    openEmailCampaign() {
        // Gathers all leads currently in the search results
        const campaignLeads = AppState.leads || [];
        
        if (campaignLeads.length === 0) {
            UI.showToast('Search results me aisi koi lead nahi hai! Pehle search run karein.', 'warning');
            return;
        }

        AppState.campaignLeads = campaignLeads.map(lead => ({
            ...lead,
            campaign_email_status: lead.email ? 'scraped' : 'missing', // scraped, missing, scanning
            campaign_draft_status: lead.custom_pitch ? 'ready' : 'not-drafted', // ready, not-drafted
            campaign_send_status: 'pending', // pending, sending, sent, failed
            campaign_subject: lead.email ? 'Digital Storefront Design Proposal' : '',
            campaign_body: lead.custom_pitch || ''
        }));

        AppState.selectedCampaignLeadId = null;

        // Render everything
        this.renderCampaignList();
        this.updateCampaignStats();
        
        // Hide review workspace empty state by default
        if (UI.el.campaignOutboxWorkspace) UI.el.campaignOutboxWorkspace.style.display = 'none';
        if (UI.el.campaignOutboxEmptyState) UI.el.campaignOutboxEmptyState.style.display = 'flex';
        if (UI.el.campaignProgressContainer) UI.el.campaignProgressContainer.style.display = 'none';

        UI.openModal('emailCampaignModal');
    },

    updateCampaignStats() {
        const leads = AppState.campaignLeads || [];
        const total = leads.length;
        const emails = leads.filter(l => l.email || l.campaign_email_status === 'scraped').length;
        const drafts = leads.filter(l => l.campaign_draft_status === 'ready').length;
        const sent = leads.filter(l => l.campaign_send_status === 'sent').length;

        if (UI.el.campaignStatLeads) UI.el.campaignStatLeads.textContent = total;
        if (UI.el.campaignStatEmails) UI.el.campaignStatEmails.textContent = emails;
        if (UI.el.campaignStatDrafts) UI.el.campaignStatDrafts.textContent = drafts;
        if (UI.el.campaignStatSent) UI.el.campaignStatSent.textContent = sent;
    },

    renderCampaignList() {
        const body = UI.el.campaignTableBody;
        if (!body) return;

        const leads = AppState.campaignLeads || [];
        
        body.innerHTML = leads.map((lead, index) => {
            const activeClass = lead.id === AppState.selectedCampaignLeadId ? 'active' : '';
            const safeName = UI.escapeHtml(lead.name);
            const safeWebsite = lead.website ? UI.escapeHtml(lead.website) : '';
            const priorityClass = `priority-${lead.priority.toLowerCase()}`;
            const priorityEmoji = { HIGH: '🔴', MEDIUM: '🟡', LOW: '🟢', IGNORE: '⚪' }[lead.priority] || '';

            // Website pill display
            let websiteLinkHtml = '';
            if (lead.website) {
                websiteLinkHtml = `<a href="${safeWebsite}" target="_blank" style="font-size: 0.72rem; color: var(--accent-cyan); text-decoration: none;">🌐 Website</a>`;
            } else {
                websiteLinkHtml = `<span style="font-size: 0.72rem; color: var(--text-muted);">❌ No Website</span>`;
            }

            // Email Status layout
            let emailHtml = '';
            if (lead.email) {
                emailHtml = `<span style="font-weight: 600; color: var(--accent-cyan); font-family: monospace;">${UI.escapeHtml(lead.email)}</span>`;
            } else if (lead.campaign_email_status === 'scanning') {
                emailHtml = `<span style="color: var(--accent-cyan); font-style: italic;">⏳ Scanning...</span>`;
            } else {
                emailHtml = `
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="color: var(--accent-red); font-size: 0.8rem;">No email</span>
                        <button class="campaign-table-btn scan" onclick="event.stopPropagation(); App.scanCampaignLeadEmailOnDemand(${lead.id}, ${index})">🔍 Scan</button>
                    </div>
                `;
            }

            // Draft Status layout
            let draftBadge = '';
            if (lead.campaign_send_status === 'sent') {
                draftBadge = `<span class="campaign-status-badge delivered">Delivered ✅</span>`;
            } else if (lead.campaign_send_status === 'failed') {
                draftBadge = `<span class="campaign-status-badge failed">Failed ❌</span>`;
            } else if (lead.campaign_send_status === 'sending') {
                draftBadge = `<span class="campaign-status-badge not-drafted">Sending...</span>`;
            } else if (lead.campaign_draft_status === 'ready') {
                draftBadge = `<span class="campaign-status-badge draft-ready">Draft Ready 🟢</span>`;
            } else {
                draftBadge = `<span class="campaign-status-badge not-drafted">No Draft ⚪</span>`;
            }

            // Action triggers
            let actionBtn = '';
            if (lead.campaign_send_status === 'sent') {
                actionBtn = `<span style="color: var(--accent-green); font-weight: bold; font-size: 0.8rem;">✓ Sent</span>`;
            } else if (lead.campaign_draft_status === 'ready') {
                actionBtn = `<button class="btn btn-whatsapp btn-sm" onclick="event.stopPropagation(); App.selectCampaignLead(${lead.id}); App.sendCampaignLeadSMTPImmediate(${lead.id}, ${index})" style="font-size: 0.7rem; padding: 4px 8px; background: var(--gradient-primary); color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: 600;">🚀 Send</button>`;
            } else if (lead.email) {
                actionBtn = `<button class="campaign-table-btn draft" onclick="event.stopPropagation(); App.selectCampaignLead(${lead.id}); App.generateCampaignLeadAIDraftImmediate(${lead.id}, ${index})">✨ Draft AI</button>`;
            } else {
                actionBtn = `<span style="color: var(--text-muted); font-size: 0.75rem;">Need Email</span>`;
            }

            return `
                <tr id="campaign-row-${lead.id}" class="${activeClass}" onclick="App.selectCampaignLead(${lead.id})">
                    <td style="padding: 10px 12px;">
                        <div style="font-weight: 700; color: var(--text-primary); max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${safeName}">${safeName}</div>
                        <div style="display: flex; align-items: center; gap: 6px; margin-top: 4px;">
                            ${websiteLinkHtml}
                            <span class="priority-badge ${priorityClass}" style="font-size: 0.65rem; padding: 1px 4px; border-radius: 3px;">${priorityEmoji} ${lead.priority}</span>
                        </div>
                    </td>
                    <td style="padding: 10px 12px;">${emailHtml}</td>
                    <td style="padding: 10px 12px; text-align: center;">${draftBadge}</td>
                    <td style="padding: 10px 12px; text-align: right;">${actionBtn}</td>
                </tr>
            `;
        }).join('');
    },

    selectCampaignLead(leadId) {
        AppState.selectedCampaignLeadId = leadId;
        
        // Highlight active table row
        document.querySelectorAll('#campaignTableBody tr').forEach(tr => tr.classList.remove('active'));
        const activeRow = document.getElementById(`campaign-row-${leadId}`);
        if (activeRow) activeRow.classList.add('active');

        const lead = (AppState.campaignLeads || []).find(l => l.id === leadId);
        if (!lead) return;

        // Toggle review panels display
        if (UI.el.campaignOutboxEmptyState) UI.el.campaignOutboxEmptyState.style.display = 'none';
        if (UI.el.campaignOutboxWorkspace) UI.el.campaignOutboxWorkspace.style.display = 'flex';

        // Load details in pane inputs
        if (UI.el.campaignSelectedName) UI.el.campaignSelectedName.textContent = lead.name;
        if (UI.el.campaignSelectedEmail) {
            UI.el.campaignSelectedEmail.textContent = lead.email || 'No email scanned yet.';
            UI.el.campaignSelectedEmail.style.color = lead.email ? 'var(--accent-cyan)' : 'var(--accent-red)';
        }
        
        const priorityBadge = UI.el.campaignSelectedPriority;
        if (priorityBadge) {
            priorityBadge.className = `priority-badge priority-${lead.priority.toLowerCase()}`;
            priorityBadge.textContent = lead.priority;
        }

        // Set subject and body
        if (UI.el.campaignSubjectInput) {
            UI.el.campaignSubjectInput.value = lead.campaign_subject || '';
        }
        if (UI.el.campaignBodyInput) {
            UI.el.campaignBodyInput.value = lead.campaign_body || '';
        }

        this.updateCampaignLivePreview();
    },

    updateCampaignLivePreview() {
        const leadId = AppState.selectedCampaignLeadId;
        const lead = (AppState.campaignLeads || []).find(l => l.id === leadId);
        if (!lead) return;

        // Sync inputs values back to state so edits are persistent
        lead.campaign_subject = UI.el.campaignSubjectInput?.value || '';
        lead.campaign_body = UI.el.campaignBodyInput?.value || '';

        // Live Preview visual card mappings
        if (UI.el.previewBusinessName) UI.el.previewBusinessName.textContent = lead.name;
        
        const brandName = localStorage.getItem('sender_brand') || 'WebScale Studio';
        if (UI.el.previewDeveloperBrand) UI.el.previewDeveloperBrand.textContent = brandName;
        
        if (UI.el.campaignEmailVisualPreview) {
            UI.el.campaignEmailVisualPreview.textContent = lead.campaign_body || 'Please draft or type a message...';
        }
    },

    async scanCampaignLeadEmailOnDemand(leadId, index) {
        const lead = (AppState.campaignLeads || []).find(l => l.id === leadId);
        if (!lead) return;

        lead.campaign_email_status = 'scanning';
        this.renderCampaignList();

        try {
            const data = await API.request(`/api/leads/${lead.id}/scan-email`, {
                method: 'POST'
            });

            if (data.success && data.email) {
                lead.email = data.email;
                lead.campaign_email_status = 'scraped';
                lead.campaign_subject = 'Digital Storefront Design Proposal';
                
                // Update active lead details inside workspace if currently selected
                if (AppState.selectedCampaignLeadId === leadId) {
                    this.selectCampaignLead(leadId);
                }
                
                UI.showToast(`📧 Found email: ${data.email} for ${lead.name}`, 'success');
            } else {
                lead.campaign_email_status = 'failed';
                UI.showToast(`✗ No email found for ${lead.name}`, 'info');
            }
        } catch (error) {
            lead.campaign_email_status = 'failed';
            UI.showToast(error.message, 'error');
        } finally {
            this.renderCampaignList();
            this.updateCampaignStats();
        }
    },

    async generateCampaignLeadAIDraftImmediate(leadId, index) {
        const lead = (AppState.campaignLeads || []).find(l => l.id === leadId);
        if (!lead) return;

        const geminiKey = localStorage.getItem('gemini_api_key');
        if (!geminiKey) {
            UI.showToast('Gemini API key set karein pehle Settings me!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        try {
            UI.showLoading(`Gemini writing email for ${lead.name}...`);
            const projectSample = this.getBestPortfolioProjectSample(lead);
            const tone = UI.el.emailToneSelect?.value || 'elite';

            const data = await API.request('/api/outreach/generate-email-ai', {
                method: 'POST',
                headers: { 'X-Gemini-API-Key': geminiKey },
                body: JSON.stringify({
                    lead: lead,
                    project_sample: projectSample,
                    tone: tone,
                    sender: {
                        name: localStorage.getItem('sender_name') || '',
                        brand: localStorage.getItem('sender_brand') || '',
                        role: localStorage.getItem('sender_role') || ''
                    },
                    custom_pitch_rules: localStorage.getItem('custom_pitch_rules') || ''
                })
            });

            if (data.success) {
                lead.campaign_subject = data.subject || 'Digital Storefront Design Proposal';
                lead.campaign_body = data.body || '';
                lead.campaign_draft_status = 'ready';
                
                // Refresh selection editor if active
                if (AppState.selectedCampaignLeadId === leadId) {
                    this.selectCampaignLead(leadId);
                }
                UI.showToast(`✨ Generated draft for ${lead.name}!`, 'success');
            } else {
                UI.showToast(data.error || 'AI Drafting failed', 'error');
            }
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            UI.hideLoading();
            this.renderCampaignList();
            this.updateCampaignStats();
        }
    },

    async generateCampaignLeadAIDraft() {
        const leadId = AppState.selectedCampaignLeadId;
        if (!leadId) return;
        
        const idx = AppState.campaignLeads.findIndex(l => l.id === leadId);
        if (idx === -1) return;

        await this.generateCampaignLeadAIDraftImmediate(leadId, idx);
    },

    skipCampaignLead() {
        const leads = AppState.campaignLeads || [];
        const currentIndex = leads.findIndex(l => l.id === AppState.selectedCampaignLeadId);
        
        if (currentIndex === -1) return;
        
        // Load next lead in list if exists
        if (currentIndex + 1 < leads.length) {
            this.selectCampaignLead(leads[currentIndex + 1].id);
        } else {
            UI.showToast('Campaign Directory list finished! You are at the end.', 'info');
        }
    },

    async sendCampaignLeadSMTPImmediate(leadId, index) {
        const lead = (AppState.campaignLeads || []).find(l => l.id === leadId);
        if (!lead) return;

        const toEmail = lead.email || '';
        const subject = lead.campaign_subject || '';
        const body = lead.campaign_body || '';

        if (!toEmail) {
            UI.showToast('Lead email address missing! Pehle website scan karein.', 'warning');
            return;
        }
        if (!subject || !body) {
            UI.showToast('Please AI draft or write email content first!', 'warning');
            return;
        }

        const host = localStorage.getItem('smtp_host');
        const port = localStorage.getItem('smtp_port');
        const email = localStorage.getItem('smtp_email');
        const password = localStorage.getItem('smtp_password');
        const useSSL = localStorage.getItem('smtp_use_ssl') === 'true';

        if (!host || !port || !email || !password) {
            UI.showToast('Direct dispatch SMTP settings NOT configured! Open settings and set them first.', 'error');
            UI.openModal('settingsModal');
            return;
        }

        try {
            UI.showLoading(`Sending SMTP outreach email to ${toEmail}...`);
            lead.campaign_send_status = 'sending';
            this.renderCampaignList();

            const data = await API.request('/api/outreach/send-smtp-email', {
                method: 'POST',
                body: JSON.stringify({
                    to_email: toEmail,
                    subject: subject,
                    body: body,
                    lead_id: lead.id,
                    smtp_config: {
                        host: host,
                        port: parseInt(port),
                        email: email,
                        password: password,
                        use_ssl: useSSL
                    }
                })
            });

            if (data.success) {
                lead.campaign_send_status = 'sent';
                
                // Locally mark contacted in primary leads list as well to keep in sync
                const mainIdx = AppState.leads.findIndex(l => l.id === lead.id);
                if (mainIdx !== -1) {
                    AppState.leads[mainIdx].contacted = 1;
                    AppState.leads[mainIdx].contact_date = new Date().toISOString();
                    AppState.leads[mainIdx].pipeline_stage = 'PITCHED';
                }
                UI.renderLeads(AppState.leads);
                UI.showToast(`Outreach email successfully sent to ${toEmail}!`, 'success');
                
                // Skip to next lead automatically after successful send!
                this.skipCampaignLead();
            } else {
                lead.campaign_send_status = 'failed';
                UI.showToast(data.error || 'SMTP Delivery failed', 'error');
            }
        } catch (error) {
            lead.campaign_send_status = 'failed';
            UI.showToast('Outreach failed: ' + error.message, 'error');
        } finally {
            UI.hideLoading();
            this.renderCampaignList();
            this.updateCampaignStats();
        }
    },

    async sendCampaignLeadSMTP() {
        const leadId = AppState.selectedCampaignLeadId;
        if (!leadId) return;

        const idx = AppState.campaignLeads.findIndex(l => l.id === leadId);
        if (idx === -1) return;

        await this.sendCampaignLeadSMTPImmediate(leadId, idx);
    },

    // ============================================================
    // Bulk Sequences Runners
    // ============================================================
    async bulkScanCampaignEmails() {
        const leads = AppState.campaignLeads || [];
        const missingLeads = leads.filter(l => !l.email && l.campaign_email_status !== 'scraped');
        
        if (missingLeads.length === 0) {
            UI.showToast('Scraping process complete! Directory me aisi koi lead nahi hai jise email scan ki zaroorat ho.', 'info');
            return;
        }

        if (!confirm(`Kya aap sabhi ${missingLeads.length} leads ke websites se email automatic deep extract karna chahte hain?`)) {
            return;
        }

        // Toggle bulk progress loaders
        const container = UI.el.campaignProgressContainer;
        const label = UI.el.campaignProgressLabel;
        const bar = UI.el.campaignProgressBar;
        const percentage = UI.el.campaignProgressPercentage;

        if (container) container.style.display = 'block';
        if (label) label.textContent = 'Auto-Scanning websites for contact emails...';

        // Disable all bulk control buttons during run
        this.toggleCampaignBulkButtons(true);

        let processed = 0;
        const total = missingLeads.length;

        for (const lead of missingLeads) {
            const idx = AppState.campaignLeads.findIndex(l => l.id === lead.id);
            if (idx === -1) continue;

            // Mark row as scanning
            lead.campaign_email_status = 'scanning';
            this.renderCampaignList();

            try {
                const data = await API.request(`/api/leads/${lead.id}/scan-email`, {
                    method: 'POST'
                });

                if (data.success && data.email) {
                    lead.email = data.email;
                    lead.campaign_email_status = 'scraped';
                    lead.campaign_subject = 'Digital Storefront Design Proposal';
                    
                    if (AppState.selectedCampaignLeadId === lead.id) {
                        this.selectCampaignLead(lead.id);
                    }
                } else {
                    lead.campaign_email_status = 'failed';
                }
            } catch (err) {
                lead.campaign_email_status = 'failed';
            }

            processed++;
            const pct = Math.round((processed / total) * 100);
            
            if (percentage) percentage.textContent = `${pct}%`;
            if (bar) bar.style.width = `${pct}%`;
            
            this.renderCampaignList();
            this.updateCampaignStats();
            
            // Add a small 200ms delay to keep UI animations smooth
            await new Promise(resolve => setTimeout(resolve, 200));
        }

        // Completed! Re-enable controls and close progress bar
        this.toggleCampaignBulkButtons(false);
        UI.showToast(`Auto-Scan finished! Processed ${total} websites successfully.`, 'success');
        
        setTimeout(() => {
            if (container) container.style.display = 'none';
        }, 3000);
    },

    async bulkDraftCampaignAI() {
        const geminiKey = localStorage.getItem('gemini_api_key');
        if (!geminiKey) {
            UI.showToast('Please configure your Gemini API Key in Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const leads = AppState.campaignLeads || [];
        const eligibleLeads = leads.filter(l => l.email && l.campaign_draft_status !== 'ready');

        if (eligibleLeads.length === 0) {
            UI.showToast('Drafting complete! Aisi koi lead nahi hai jiske paas email address ho aur draft tayyar na ho.', 'info');
            return;
        }

        if (!confirm(`Kya aap Gemini AI ke through sabhi ${eligibleLeads.length} leads ke liye automatically 100% unique personalized pitches write karna chahte hain?`)) {
            return;
        }

        const container = UI.el.campaignProgressContainer;
        const label = UI.el.campaignProgressLabel;
        const bar = UI.el.campaignProgressBar;
        const percentage = UI.el.campaignProgressPercentage;

        if (container) container.style.display = 'block';
        if (label) label.textContent = 'Gemini AI generating personalized outbox pitches...';
        if (bar) bar.style.width = '0%';
        if (percentage) percentage.textContent = '0%';

        this.toggleCampaignBulkButtons(true);

        let processed = 0;
        const total = eligibleLeads.length;

        for (const lead of eligibleLeads) {
            try {
                const projectSample = this.getBestPortfolioProjectSample(lead);
                const tone = UI.el.emailToneSelect?.value || 'elite';

                const data = await API.request('/api/outreach/generate-email-ai', {
                    method: 'POST',
                    headers: { 'X-Gemini-API-Key': geminiKey },
                    body: JSON.stringify({
                        lead: lead,
                        project_sample: projectSample,
                        tone: tone,
                        sender: {
                            name: localStorage.getItem('sender_name') || '',
                            brand: localStorage.getItem('sender_brand') || '',
                            role: localStorage.getItem('sender_role') || ''
                        },
                        custom_pitch_rules: localStorage.getItem('custom_pitch_rules') || ''
                    })
                });

                if (data.success) {
                    lead.campaign_subject = data.subject || 'Digital Storefront Design Proposal';
                    lead.campaign_body = data.body || '';
                    lead.campaign_draft_status = 'ready';
                    
                    if (AppState.selectedCampaignLeadId === lead.id) {
                        this.selectCampaignLead(lead.id);
                    }
                }
            } catch (err) {
                console.error(`AI generating failed for lead ${lead.name}:`, err);
            }

            processed++;
            const pct = Math.round((processed / total) * 100);
            
            if (percentage) percentage.textContent = `${pct}%`;
            if (bar) bar.style.width = `${pct}%`;
            
            this.renderCampaignList();
            this.updateCampaignStats();
            
            await new Promise(resolve => setTimeout(resolve, 200));
        }

        this.toggleCampaignBulkButtons(false);
        UI.showToast(`✨ Auto-Drafting complete! Ready to send: ${processed} campaign emails.`, 'success');
        
        setTimeout(() => {
            if (container) container.style.display = 'none';
        }, 3000);
    },

    async bulkSendCampaignSMTP() {
        const host = localStorage.getItem('smtp_host');
        const port = localStorage.getItem('smtp_port');
        const email = localStorage.getItem('smtp_email');
        const password = localStorage.getItem('smtp_password');
        const useSSL = localStorage.getItem('smtp_use_ssl') === 'true';

        if (!host || !port || !email || !password) {
            UI.showToast('Please configure your Direct SMTP Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const leads = AppState.campaignLeads || [];
        const sendableLeads = leads.filter(l => l.campaign_draft_status === 'ready' && l.campaign_send_status !== 'sent');

        if (sendableLeads.length === 0) {
            UI.showToast('Campaign complete! Aisi koi lead nahi hai jiske paas "Draft Ready" state ho.', 'warning');
            return;
        }

        if (!confirm(`🚀 WARNING (Mass Dispatching Campaign!)\n\nKya aap sabhi ${sendableLeads.length} leads ke liye instant SMTP direct cold emails launch karna chahte hain?`)) {
            return;
        }

        const container = UI.el.campaignProgressContainer;
        const label = UI.el.campaignProgressLabel;
        const bar = UI.el.campaignProgressBar;
        const percentage = UI.el.campaignProgressPercentage;

        if (container) container.style.display = 'block';
        if (label) label.textContent = '🚀 Dispatching cold campaign outreach emails...';
        if (bar) bar.style.width = '0%';
        if (percentage) percentage.textContent = '0%';

        this.toggleCampaignBulkButtons(true);

        let processed = 0;
        const total = sendableLeads.length;

        for (const lead of sendableLeads) {
            const idx = AppState.campaignLeads.findIndex(l => l.id === lead.id);
            if (idx === -1) continue;

            lead.campaign_send_status = 'sending';
            this.renderCampaignList();

            try {
                const data = await API.request('/api/outreach/send-smtp-email', {
                    method: 'POST',
                    body: JSON.stringify({
                        to_email: lead.email,
                        subject: lead.campaign_subject,
                        body: lead.campaign_body,
                        lead_id: lead.id,
                        smtp_config: {
                            host: host,
                            port: parseInt(port),
                            email: email,
                            password: password,
                            use_ssl: useSSL
                        }
                    })
                });

                if (data.success) {
                    lead.campaign_send_status = 'sent';
                    
                    // Update main results list contacted state in local memory
                    const mainIdx = AppState.leads.findIndex(l => l.id === lead.id);
                    if (mainIdx !== -1) {
                        AppState.leads[mainIdx].contacted = 1;
                        AppState.leads[mainIdx].contact_date = new Date().toISOString();
                        AppState.leads[mainIdx].pipeline_stage = 'PITCHED';
                    }
                } else {
                    lead.campaign_send_status = 'failed';
                }
            } catch (err) {
                lead.campaign_send_status = 'failed';
            }

            processed++;
            const pct = Math.round((processed / total) * 100);
            
            if (percentage) percentage.textContent = `${pct}%`;
            if (bar) bar.style.width = `${pct}%`;
            
            this.renderCampaignList();
            this.updateCampaignStats();

            // Anti-Spam mass delivery delay: 1.5 seconds wait interval between SMTP requests
            await new Promise(resolve => setTimeout(resolve, 1500));
        }

        this.toggleCampaignBulkButtons(false);
        UI.renderLeads(AppState.leads);
        UI.showToast(`Campaign finished! Delivered successfully: ${processed} outreach cold emails.`, 'success');
        
        setTimeout(() => {
            if (container) container.style.display = 'none';
        }, 3000);
    },

    toggleCampaignBulkButtons(disabled) {
        if (UI.el.campaignBulkScanBtn) UI.el.campaignBulkScanBtn.disabled = disabled;
        if (UI.el.campaignBulkDraftBtn) UI.el.campaignBulkDraftBtn.disabled = disabled;
        if (UI.el.campaignBulkSendBtn) UI.el.campaignBulkSendBtn.disabled = disabled;
        if (UI.el.campaignSelectedSendBtn) UI.el.campaignSelectedSendBtn.disabled = disabled;
        if (UI.el.campaignSelectedAIGenBtn) UI.el.campaignSelectedAIGenBtn.disabled = disabled;
        
        // Visual indicator adjustments
        const btns = [UI.el.campaignBulkScanBtn, UI.el.campaignBulkDraftBtn, UI.el.campaignBulkSendBtn];
        btns.forEach(btn => {
            if (btn) btn.style.opacity = disabled ? '0.5' : '1';
        });
    }
};

// ============================================================
// Initialize on DOM ready
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
