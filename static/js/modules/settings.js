/**
 * LeadHunter AI — Settings Module
 */

import { API } from './api.js';
import { UI } from './ui.js';
import { AppState } from './state.js';
import { CryptoHelper } from './crypto.js';

export const settingsModule = {
    async checkConfig() {
        try {
            const localKey = localStorage.getItem('serpapi_key');
            const data = await API.getConfig();
            AppState.hasApiKey = !!localKey || data.has_api_key;
            
            const statusEl = UI.el.apiKeyStatus;
            const settingsStatus = document.getElementById('settingsApiKeyStatus');
            
            if (localKey) {
                if (statusEl) {
                    statusEl.className = 'api-key-status active';
                    statusEl.textContent = '✓ Your Key';
                }
                if (settingsStatus) {
                    settingsStatus.className = 'api-key-status active';
                    settingsStatus.textContent = '✓ Using Your Local API Key';
                }
            } else if (data.has_api_key) {
                if (statusEl) {
                    statusEl.className = 'api-key-status active';
                    statusEl.textContent = '✓ Connected';
                }
                if (settingsStatus) {
                    settingsStatus.className = 'api-key-status active';
                    settingsStatus.textContent = '✓ Server Default Key Connected';
                }
            } else {
                if (statusEl) {
                    statusEl.className = 'api-key-status inactive';
                    statusEl.textContent = '✗ Not Set';
                }
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
        if (!UI.el.apiKeyInput) return;
        const apiKey = UI.el.apiKeyInput.value.trim();
        
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
            await API.saveConfig(apiKey);
            
            const encryptedKey = await CryptoHelper.encrypt(apiKey, AppState.encryptionKey);
            localStorage.setItem('serpapi_key', encryptedKey);
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

    async checkGeminiConfig() {
        const geminiKey = localStorage.getItem('gemini_api_key');
        const decryptedKey = geminiKey ? await CryptoHelper.decrypt(geminiKey, AppState.encryptionKey) : '';
        const statusEl = UI.el.geminiApiKeyStatus;
        if (decryptedKey) {
            if (statusEl) {
                statusEl.className = 'api-key-status active';
                statusEl.textContent = '✓ Configured';
            }
            if (UI.el.geminiApiKeyInput) {
                UI.el.geminiApiKeyInput.value = decryptedKey;
            }
        } else {
            if (statusEl) {
                statusEl.className = 'api-key-status inactive';
                statusEl.textContent = '✗ Not Set';
            }
            if (UI.el.geminiApiKeyInput) {
                UI.el.geminiApiKeyInput.value = '';
            }
        }
    },

    async saveGeminiApiKey() {
        const geminiKey = UI.el.geminiApiKeyInput.value.trim();
        
        if (!geminiKey) {
            localStorage.removeItem('gemini_api_key');
            await this.checkGeminiConfig();
            UI.showToast('Gemini API key cleared successfully!', 'info');
            return;
        }

        if (!geminiKey.startsWith('AIza') && !geminiKey.startsWith('AQ.')) {
            UI.showToast('Invalid format! Gemini API keys must start with "AIza" or "AQ." (e.g. AIzaSy... or AQ.Ab8...).', 'error');
            return;
        }

        const encryptedKey = await CryptoHelper.encrypt(geminiKey, AppState.encryptionKey);
        localStorage.setItem('gemini_api_key', encryptedKey);
        await this.checkGeminiConfig();
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

    async checkSmtpConfig() {
        const host = localStorage.getItem('smtp_host') || '';
        const port = localStorage.getItem('smtp_port') || '';
        const email = localStorage.getItem('smtp_email') || '';
        const password = localStorage.getItem('smtp_password') || '';
        const decryptedPassword = password ? await CryptoHelper.decrypt(password, AppState.encryptionKey) : '';
        const useSSL = localStorage.getItem('smtp_use_ssl') !== 'false';

        if (UI.el.smtpHostInput) UI.el.smtpHostInput.value = host;
        if (UI.el.smtpPortInput) UI.el.smtpPortInput.value = port;
        if (UI.el.smtpEmailInput) UI.el.smtpEmailInput.value = email;
        if (UI.el.smtpPasswordInput) UI.el.smtpPasswordInput.value = decryptedPassword;
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

    async saveSmtpSettings() {
        const host = UI.el.smtpHostInput?.value.trim() || '';
        const port = UI.el.smtpPortInput?.value.trim() || '';
        const email = UI.el.smtpEmailInput?.value.trim() || '';
        const password = UI.el.smtpPasswordInput?.value.trim() || '';
        const useSSL = UI.el.smtpUseSSL ? UI.el.smtpUseSSL.checked : true;

        if (!host || !port || !email || !password) {
            UI.showToast('Please fill in all SMTP fields before saving.', 'warning');
            return;
        }

        const encryptedPassword = await CryptoHelper.encrypt(password, AppState.encryptionKey);
        localStorage.setItem('smtp_host', host);
        localStorage.setItem('smtp_port', port);
        localStorage.setItem('smtp_email', email);
        localStorage.setItem('smtp_password', encryptedPassword);
        localStorage.setItem('smtp_use_ssl', useSSL ? 'true' : 'false');

        await this.checkSmtpConfig();
        UI.showToast('SMTP credentials saved securely to your browser!', 'success');
    }
};
