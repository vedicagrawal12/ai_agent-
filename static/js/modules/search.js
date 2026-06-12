/**
 * LeadHunter AI — Search Module
 */

import { API } from './api.js';
import { UI } from './ui.js';
import { AppState } from './state.js';

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

export const searchModule = {
    suggestZones() {
        const city = UI.el.cityInput.value.trim().toLowerCase();
        if (!city) {
            UI.el.deepScanZonesInput.value = '';
            return;
        }
        
        const matchedKey = Object.keys(SUB_LOCALITIES).find(k => k === city || city.includes(k));
        if (matchedKey) {
            UI.el.deepScanZonesInput.value = SUB_LOCALITIES[matchedKey].join(', ');
        } else {
            const rawCity = UI.el.cityInput.value.trim();
            UI.el.deepScanZonesInput.value = `North ${rawCity}, South ${rawCity}, East ${rawCity}, West ${rawCity}, Central ${rawCity}`;
        }
    },

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

            const submitData = await API.search(query, city, maxResults, includeWithWebsite, hideSaved, deepScan, zones, 0);
            if (!submitData.success || !submitData.task_id) {
                throw new Error(submitData.error || "Failed to start search task.");
            }
            
            const taskId = submitData.task_id;
            let pollResult = null;
            
            while (true) {
                await new Promise(resolve => setTimeout(resolve, 1500));
                const statusData = await API.getSearchStatus(taskId);
                if (statusData.status === 'DONE') {
                    pollResult = statusData.result;
                    break;
                } else if (statusData.status === 'FAILED') {
                    throw new Error(statusData.error || "Search task failed.");
                } else if (statusData.status === 'NOT_FOUND') {
                    throw new Error("Search task not found.");
                }
            }
            
            const data = pollResult;
            
            AppState.leads = data.leads;
            AppState.allResults = data.all_results;
            AppState.stats = data.stats;
            
            UI.updateStats(data.stats);
            UI.renderLeads(data.leads);
            
            UI.el.resultsTitle.textContent = `Results for "${data.query}"`;
            
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
            if (UI.el.loadMoreBtn) {
                UI.el.loadMoreBtn.disabled = true;
                UI.el.loadMoreBtn.innerHTML = '⏳ Loading Next Page...';
            }

            AppState.currentOffset += params.maxResults;
            UI.showLoading(`Loading page offset starting at ${AppState.currentOffset}...`);

            const submitData = await API.search(
                params.query,
                params.city,
                params.maxResults,
                params.includeWithWebsite,
                params.hideSaved,
                params.deepScan,
                params.zones,
                AppState.currentOffset
            );

            if (!submitData.success || !submitData.task_id) {
                throw new Error(submitData.error || "Failed to start search task.");
            }
            
            const taskId = submitData.task_id;
            let pollResult = null;
            
            while (true) {
                await new Promise(resolve => setTimeout(resolve, 1500));
                const statusData = await API.getSearchStatus(taskId);
                if (statusData.status === 'DONE') {
                    pollResult = statusData.result;
                    break;
                } else if (statusData.status === 'FAILED') {
                    throw new Error(statusData.error || "Search task failed.");
                } else if (statusData.status === 'NOT_FOUND') {
                    throw new Error("Search task not found.");
                }
            }
            
            const data = pollResult;

            if (data.leads && data.leads.length > 0) {
                AppState.leads = AppState.leads.concat(data.leads);
                AppState.allResults = AppState.allResults.concat(data.all_results);
                
                const pageStats = data.stats;
                AppState.stats.total_found = (AppState.stats.total_found || 0) + (pageStats.total_found || 0);
                AppState.stats.leads_count = (AppState.stats.leads_count || 0) + (pageStats.leads_count || 0);
                AppState.stats.broken_websites = (AppState.stats.broken_websites || 0) + (pageStats.broken_websites || 0);
                AppState.stats.high_priority = (AppState.stats.high_priority || 0) + (pageStats.high_priority || 0);
                AppState.stats.medium_priority = (AppState.stats.medium_priority || 0) + (pageStats.medium_priority || 0);
                AppState.stats.with_phone = (AppState.stats.with_phone || 0) + (pageStats.with_phone || 0);
                AppState.stats.with_whatsapp = (AppState.stats.with_whatsapp || 0) + (pageStats.with_whatsapp || 0);
                UI.updateStats(AppState.stats);
                
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

    switchView(view) {
        AppState.currentView = view;
        
        const listBtn = document.getElementById('listViewBtn');
        const kanbanBtn = document.getElementById('kanbanViewBtn');
        const analyticsBtn = document.getElementById('analyticsViewBtn');
        
        if (listBtn) listBtn.classList.remove('active');
        if (kanbanBtn) kanbanBtn.classList.remove('active');
        if (analyticsBtn) analyticsBtn.classList.remove('active');
        
        if (view === 'kanban') {
            if (kanbanBtn) kanbanBtn.classList.add('active');
        } else if (view === 'analytics') {
            if (analyticsBtn) analyticsBtn.classList.add('active');
        } else {
            if (listBtn) listBtn.classList.add('active');
        }
        
        UI.renderLeads(AppState.leads);
    },

    async loadHistory() {
        try {
            const data = await API.getHistory();
            const container = document.getElementById('historyList');
            
            if (data.history && data.history.length > 0) {
                AppState.searchHistory = data.history;

                container.innerHTML = data.history.map((item, idx) => `
                    <div class="history-item" data-history-index="${idx}">
                        <div>
                            <div class="history-query">🔍 ${UI.escapeHtml(item.query)}${item.deep_scan ? ' (Deep Scan)' : ''} in ${UI.escapeHtml(item.city)}</div>
                        </div>
                        <div class="history-meta">
                            <span>📊 ${item.results_count} found</span>
                            <span>🎯 ${item.leads_count} leads</span>
                            <span>📅 ${new Date(item.searched_at).toLocaleDateString()}</span>
                        </div>
                    </div>
                `).join('');

                container.querySelectorAll('.history-item[data-history-index]').forEach(el => {
                    el.addEventListener('click', () => {
                        const idx = parseInt(el.getAttribute('data-history-index'));
                        const item = AppState.searchHistory[idx];
                        if (item) {
                            this.rerunSearch(item);
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

    rerunSearch(item) {
        UI.el.queryInput.value = item.query;
        UI.el.cityInput.value = item.city;
        
        // Restore deep_scan, zones, include_with_website, and hide_saved options
        if (UI.el.deepScanToggle) {
            UI.el.deepScanToggle.checked = item.deep_scan || false;
            // Dispatch change event to update the zones container visibility
            UI.el.deepScanToggle.dispatchEvent(new Event('change'));
        }
        if (UI.el.deepScanZonesInput) {
            UI.el.deepScanZonesInput.value = item.zones || "";
        }
        if (UI.el.includeWebsiteToggle) {
            UI.el.includeWebsiteToggle.checked = item.include_with_website || false;
        }
        if (UI.el.hideSavedLeadsToggle) {
            UI.el.hideSavedLeadsToggle.checked = item.hide_saved || false;
        }
        
        UI.closeModal('historyModal');
        this.handleSearch();
    }
};
