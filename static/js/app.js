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
    activeSearchParams: null
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
            
            // Bulk Actions Elements
            bulkScanSocialsBtn: document.getElementById('bulkScanSocialsBtn'),
            bulkProgressBanner: document.getElementById('bulkProgressBanner'),
            bulkProgressLabel: document.getElementById('bulkProgressLabel'),
            bulkProgressPercentage: document.getElementById('bulkProgressPercentage'),
            bulkProgressBar: document.getElementById('bulkProgressBar'),
            
            toastContainer: document.getElementById('toastContainer'),
        };
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
            if (this.el.loadMoreContainer) this.el.loadMoreContainer.style.display = 'none';
            return;
        }
        
        this.el.emptyState.style.display = 'none';
        this.el.tableContainer.style.display = 'block';
        
        this.el.leadsTableBody.innerHTML = leads.map((lead, i) => this.createLeadRow(lead, i)).join('');
        
        // Show/hide Load More button based on if we fetched any results
        if (this.el.loadMoreContainer) {
            const maxResults = AppState.activeSearchParams ? AppState.activeSearchParams.maxResults : 20;
            // If the active list is a multiple of maxResults (or close), there could be more
            // If it's 0 or we fetched a small page, hide it.
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
        const icons = { success: '✅', error: '❌', info: 'ℹ️' };
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <span class="toast-message">${message}</span>
        `;
        
        this.el.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('toast-exit');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
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
                customArea.style.display = e.target.value === 'custom' ? 'block' : 'none';
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
                    }
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
                    previous_pitch: previousPitch
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

        // Build pitch message using current selected template
        let message = '';
        const template = AppState.selectedTemplate;
        if (template === 'custom') {
            message = document.getElementById('messagePreview')?.textContent || 
                      document.getElementById('customMessageInput')?.value || '';
        }
        
        if (!message) {
            const templateKey = (template === 'custom' || !template) ? 'website_pitch' : template;
            const templateData = AppState.whatsappTemplates[templateKey];
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
                
                // Update stats (combine or overwrite)
                AppState.stats = data.stats;
                UI.updateStats(data.stats);
                
                // Re-render
                UI.renderLeads(AppState.leads);
                
                UI.showToast(`Loaded ${data.stats.leads_count} more leads! Total leads in view: ${AppState.leads.length}`, 'success');
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

        // Add click handlers for visual selection
        container.querySelectorAll('.template-option').forEach(option => {
            option.addEventListener('click', () => {
                container.querySelectorAll('.template-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
            });
        });
    },

    openWhatsApp(index) {
        const lead = AppState.leads[index];
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
                container.innerHTML = data.history.map(item => `
                    <div class="history-item" onclick="App.rerunSearch('${item.query}', '${item.city}')">
                        <div>
                            <div class="history-query">🔍 ${item.query} in ${item.city}</div>
                        </div>
                        <div class="history-meta">
                            <span>📊 ${item.results_count} found</span>
                            <span>🎯 ${item.leads_count} leads</span>
                            <span>📅 ${new Date(item.searched_at).toLocaleDateString()}</span>
                        </div>
                    </div>
                `).join('');
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

        const serpKey = localStorage.getItem('serpapi_api_key') || '';
        const localSerpKey = localStorage.getItem('api_key') || ''; // Check alternative names
        
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
                    method: 'POST',
                    headers: {
                        'X-SerpApi-Key': serpKey || localSerpKey
                    }
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
    }
};

// ============================================================
// Initialize on DOM ready
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
