/**
 * LeadHunter AI — API Client Module
 */

import { CryptoHelper } from './crypto.js';
import { AppState } from './state.js';

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

export const API = {
    baseUrl: '',

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const csrfToken = getCookie('csrf_token');
        const mergedHeaders = {
            'Content-Type': 'application/json',
            ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
            ...(options.headers || {})
        };

        const config = {
            ...options,
            headers: mergedHeaders
        };

        // Inject SerpApi Key locally if present
        const localKey = localStorage.getItem('serpapi_key');
        if (localKey) {
            const decryptedKey = await CryptoHelper.decrypt(localKey, AppState.encryptionKey);
            if (decryptedKey) {
                config.headers['X-SerpApi-Key'] = decryptedKey;
            }
        }

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                let errorMessage = `Request failed with status ${response.status}`;
                try {
                    const data = await response.json();
                    errorMessage = data.error || errorMessage;
                } catch (_) {
                    if (response.status === 404) {
                        errorMessage = `API endpoint not found (404). Run Flask backend server with 'python app.py' and open http://localhost:5000 in your browser.`;
                    }
                }
                throw new Error(errorMessage);
            }
            
            try {
                return await response.json();
            } catch (jsonError) {
                throw new Error(`Invalid server response (not valid JSON).`);
            }
        } catch (error) {
            if (error.message.includes('Failed to fetch') || error.name === 'TypeError') {
                throw new Error('Cannot connect to server. Make sure the Flask backend is running on http://localhost:5000.');
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
        const csrfToken = getCookie('csrf_token');
        const response = await fetch('/api/export/excel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {})
            },
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

    async getSearchStatus(taskId) {
        return this.request(`/api/search/status/${taskId}`);
    },

    async getSavedLeads(priority = null, city = null) {
        const params = new URLSearchParams();
        if (priority) params.append('priority', priority);
        if (city) params.append('city', city);
        return this.request(`/api/leads?${params.toString()}`);
    }
};
