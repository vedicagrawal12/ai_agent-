/**
 * LeadHunter AI — UI Module
 */

import { API } from './api.js';
import { AppState } from './state.js';

export const UI = {
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
            welcomeHero: document.getElementById('welcomeHero'),
            
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
            pitchServiceSelect: document.getElementById('pitchServiceSelect'),
            pitchCustomServiceContainer: document.getElementById('pitchCustomServiceContainer'),
            pitchCustomServiceInput: document.getElementById('pitchCustomServiceInput'),
            pitchToneSelect: document.getElementById('pitchToneSelect'),
            pitchLengthSelect: document.getElementById('pitchLengthSelect'),
            pitchMinWordsSelect: document.getElementById('pitchMinWordsSelect'),
            pitchLanguageSelect: document.getElementById('pitchLanguageSelect'),
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
            emailServiceSelect: document.getElementById('emailServiceSelect'),
            emailCustomServiceContainer: document.getElementById('emailCustomServiceContainer'),
            emailCustomServiceInput: document.getElementById('emailCustomServiceInput'),
            emailToneSelect: document.getElementById('emailToneSelect'),
            emailMinWordsSelect: document.getElementById('emailMinWordsSelect'),
            emailLanguageSelect: document.getElementById('emailLanguageSelect'),
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

        this._kanbanAbortController = null;
    },

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

    updateStats(stats) {
        this.el.statsBar.style.display = 'grid';
        if (window.gsap) {
            window.gsap.fromTo('.stat-card', 
                { opacity: 0, y: 15 }, 
                { opacity: 1, y: 0, duration: 0.4, stagger: 0.05, ease: 'power2.out', overwrite: 'auto' }
            );
        }
        
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

    renderLeads(leads) {
        AppState.leads = leads;
        
        this.el.resultsSection.style.display = 'block';
        if (window.gsap) {
            window.gsap.fromTo(this.el.resultsSection, 
                { opacity: 0, y: 20 }, 
                { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out', overwrite: 'auto' }
            );
        }
        
        if (leads.length === 0) {
            this.el.emptyState.style.display = 'block';
            this.el.tableContainer.style.display = 'none';
            if (this.el.kanbanContainer) this.el.kanbanContainer.style.display = 'none';
            if (this.el.loadMoreContainer) this.el.loadMoreContainer.style.display = 'none';
            if (this.el.welcomeHero) this.el.welcomeHero.style.display = 'block';
            return;
        }
        
        if (this.el.welcomeHero) this.el.welcomeHero.style.display = 'none';
        this.el.emptyState.style.display = 'none';
        
        const analyticsContainer = document.getElementById('analyticsContainer');
        if (AppState.currentView === 'analytics') {
            this.el.tableContainer.style.display = 'none';
            if (this.el.kanbanContainer) this.el.kanbanContainer.style.display = 'none';
            if (analyticsContainer) analyticsContainer.style.display = 'block';
            if (window.App && typeof window.App.refreshAnalytics === 'function') {
                window.App.refreshAnalytics();
            }
        } else {
            if (analyticsContainer) analyticsContainer.style.display = 'none';
            if (AppState.currentView === 'kanban') {
                this.el.tableContainer.style.display = 'none';
                if (this.el.kanbanContainer) this.el.kanbanContainer.style.display = 'block';
                this.renderKanbanBoard(leads);
                if (window.gsap) {
                    window.gsap.fromTo('.kanban-column', 
                        { opacity: 0, y: 15 }, 
                        { opacity: 1, y: 0, duration: 0.4, stagger: 0.08, ease: 'power2.out', overwrite: 'auto' }
                    );
                    window.gsap.fromTo('.kanban-card', 
                        { opacity: 0, y: 10 }, 
                        { opacity: 1, y: 0, duration: 0.3, stagger: 0.02, ease: 'power1.out', delay: 0.15, overwrite: 'auto' }
                    );
                }
            } else {
                this.el.tableContainer.style.display = 'block';
                if (this.el.kanbanContainer) this.el.kanbanContainer.style.display = 'none';
                this.el.leadsTableBody.innerHTML = leads.map((lead, i) => this.createLeadRow(lead, i)).join('');
                if (window.gsap) {
                    window.gsap.fromTo('.leads-table tbody tr', 
                        { opacity: 0, x: -8 }, 
                        { opacity: 1, x: 0, duration: 0.35, stagger: 0.015, ease: 'power1.out', overwrite: 'auto' }
                    );
                }
            }
        }
        
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
            const sanitizedWebsite = this.sanitizeUrl(lead.website);
            if (lead.is_broken_website) {
                websiteDisplay = `<a href="${sanitizedWebsite}" target="_blank" class="broken-website-badge" data-tooltip="BROKEN SITE: ${safeWebsite}">⚠️ Broken Site</a>`;
            } else {
                websiteDisplay = `<a href="${sanitizedWebsite}" target="_blank" class="website-link" data-tooltip="${safeWebsite}"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="width: 13px; height: 13px; stroke: currentColor; fill: none; stroke-width: 2; display: inline-block; vertical-align: middle; margin-right: 4px;"><path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9 9 0 100-18 9 9 0 000 18zm0 0V3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 18c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3M3.75 6h16.5M3.75 12h16.5m-16.5 6h16.5" /></svg>Visit Site</a>`;
            }
        } else {
            websiteDisplay = `<span class="no-website"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="width: 12px; height: 12px; stroke: var(--text-muted); fill: none; stroke-width: 2; display: inline-block; vertical-align: middle; margin-right: 4px;"><path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" /></svg>No Website</span>`;
        }
            
        let whatsappBtn = '';
        if (lead.whatsapp_number) {
            if (lead.line_type === 'LANDLINE') {
                whatsappBtn = `<button class="row-btn whatsapp disabled-landline" data-tooltip="Landline Number (No WhatsApp)" disabled><svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48L4.25 21l3.59-.87A8.966 8.966 0 0 0 12 20.25Z" /></svg></button>`;
            } else {
                whatsappBtn = `<button class="row-btn whatsapp" data-tooltip="Send WhatsApp Message" onclick="App.openWhatsApp(${index})"><svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48L4.25 21l3.59-.87A8.966 8.966 0 0 0 12 20.25Z" /></svg></button>`;
            }
        }

        let emailBtn = '';
        if (lead.email) {
            emailBtn = `<button class="row-btn email" data-tooltip="Send Email Outreach" onclick="App.openEmail(${index})"><svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" /></svg></button>`;
        } else {
            const tooltip = lead.website ? "Scan Website/Web for Email" : "Search Web for Email (SerpApi)";
            emailBtn = `<button class="row-btn scan-email-btn" id="scanEmailBtn-${index}" data-tooltip="${tooltip}" onclick="App.scanEmail(${lead.id}, ${index})"><svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 15.75l-2.489-2.489m0 0a3.375 3.375 0 10-4.773-4.773 3.375 3.375 0 004.774 4.774ZM21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25" /></svg></button>`;
        }
        
        const mapsQuery = encodeURIComponent(`${lead.name} ${lead.address || lead.city}`);
        const mapsLink = lead.place_id 
            ? `https://www.google.com/maps/search/?api=1&query=${mapsQuery}&query_place_id=${lead.place_id}`
            : `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`;
        
        let socialsDisplay = '';
        if (lead.instagram || lead.facebook) {
            if (lead.instagram) {
                socialsDisplay += `<button class="row-btn instagram" data-tooltip="Instagram DM & Auto-Copy" onclick="App.openInstagram(${index})" style="background: var(--accent-blue); color: white; border: none; font-size: 0.75rem; padding: 3px 6px; border-radius: 4px; margin-right: 4px; cursor: pointer;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="width: 12px; height: 12px; stroke: currentColor; fill: none; stroke-width: 2; display: inline-block; vertical-align: middle; margin-right: 4px;"><path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316A2.192 2.192 0 0 0 14.54 3.75h-5.08c-.73 0-1.402.36-1.8 1.003l-.833 1.334ZM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg>DM</button>`;
            }
            if (lead.facebook) {
                const sanitizedFacebook = this.sanitizeUrl(lead.facebook);
                socialsDisplay += `<a href="${sanitizedFacebook}" target="_blank" class="row-btn facebook" data-tooltip="Facebook Profile" style="background: var(--accent-blue); color: white; font-size: 0.75rem; padding: 3px 6px; border-radius: 4px; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; height: 23px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="width: 12px; height: 12px; stroke: currentColor; fill: none; stroke-width: 2; display: inline-block; vertical-align: middle; margin-right: 4px;"><path stroke-linecap="round" stroke-linejoin="round" d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" /></svg>Page</a>`;
            }
        } else {
            const scanId = lead.id || '';
            if (scanId) {
                socialsDisplay = `<button class="row-btn" id="scanSocialBtn-${index}" onclick="App.scanSocials(${scanId}, ${index})" style="font-size: 0.75rem; padding: 3px 6px; background: rgba(0,212,255,0.1); border: 1px solid var(--accent-cyan); color: var(--accent-cyan); border-radius: 4px; cursor: pointer;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="width: 12px; height: 12px; stroke: currentColor; fill: none; stroke-width: 2; display: inline-block; vertical-align: middle; margin-right: 4px;"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196a7.5 7.5 0 0010.607 10.607z" /></svg>Scan Socials</button>`;
            } else {
                socialsDisplay = `<span style="color: var(--text-muted); font-size: 0.8rem;">Save first to Scan</span>`;
            }
        }
 
        return `
            <tr data-lead-id="${lead.id || ''}" onclick="App.handleRowClick(event, ${index})" style="cursor: pointer;">
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
                        <a href="${mapsLink}" target="_blank" class="row-btn" data-tooltip="View on Google Maps"><svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" /></svg></a>
                        ${whatsappBtn}
                        ${emailBtn}
                        <button class="row-btn mockup" data-tooltip="Copy Mockup Link" onclick="App.copyMockupLink(${lead.id})"><svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10.5 1.5H13.5A2.25 2.25 0 0 1 15.75 3.75V20.25A2.25 2.25 0 0 1 13.5 22.5H10.5A2.25 2.25 0 0 1 8.25 20.25V3.75a2.25 2.25 0 0 1 2.25-2.25z" /><path stroke-linecap="round" stroke-linejoin="round" d="M12 18.75h.008v.008H12V18.75z" /></svg></button>
                        <button class="row-btn" data-tooltip="Copy Phone" onclick="App.copyPhone(${index})"><svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 8.25V6a2.25 2.25 0 0 0-2.25-2.25H6A2.25 2.25 0 0 0 3.75 6v8.25A2.25 2.25 0 0 0 6 16.5h2.25m8.25-8.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-7.5A2.25 2.25 0 0 1 8.25 18v-1.5m8.25-8.25h-6A2.25 2.25 0 0 0 8.25 12V18" /></svg></button>
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

    renderKanbanBoard(leads) {
        const columns = ['NEW', 'PITCHED', 'INTERESTED', 'REPLIED', 'CONVERTED', 'IGNORED'];
        
        columns.forEach(stage => {
            const cardsContainer = document.querySelector(`.kanban-cards[data-stage="${stage}"]`);
            if (cardsContainer) {
                cardsContainer.innerHTML = '';
            }
            const columnEl = document.querySelector(`.kanban-column[data-stage="${stage}"]`);
            const countBadge = columnEl?.querySelector('.column-count');
            if (countBadge) countBadge.textContent = '0';
        });
        
        const counts = { NEW: 0, PITCHED: 0, INTERESTED: 0, REPLIED: 0, CONVERTED: 0, IGNORED: 0 };
        
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
        
        columns.forEach(stage => {
            const columnEl = document.querySelector(`.kanban-column[data-stage="${stage}"]`);
            const countBadge = columnEl?.querySelector('.column-count');
            if (countBadge) {
                countBadge.textContent = counts[stage];
            }
        });
        
        this.initKanbanDragAndDrop();
    },

    createKanbanCard(lead) {
        const card = document.createElement('div');
        card.className = 'kanban-card';
        card.setAttribute('draggable', 'true');
        card.setAttribute('data-id', lead.id);
        
        const priorityClass = (lead.priority || 'LOW').toUpperCase();
        
        let siteLabel = '';
        if (lead.is_broken_website) {
            siteLabel = `<span style="color: var(--accent-red); font-size: 0.7rem; font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">⚠️ Broken site</span>`;
        } else if (lead.website) {
            siteLabel = `<span style="color: var(--accent-green); font-size: 0.7rem; font-weight: 500;">✓ Website</span>`;
        } else {
            siteLabel = `<span style="color: var(--text-muted); font-size: 0.7rem;">No website</span>`;
        }
        
        let actionsHtml = '';
        const idx = AppState.leads.findIndex(l => l.id === lead.id);
        card.setAttribute('onclick', `App.handleRowClick(event, ${idx})`);
        card.style.cursor = 'pointer';
        
        if (lead.instagram || lead.facebook) {
            if (lead.instagram) {
                actionsHtml += `<button class="kanban-card-btn instagram" title="Instagram DM & Auto-Copy" onclick="App.openInstagram(${idx})" style="background: var(--accent-blue); color: white; border-radius: 4px; padding: 4px 8px; font-size: 0.75rem; font-weight: 600; border: none; display: flex; align-items: center; gap: 4px; cursor: pointer;">📸 DM</button>`;
            }
            if (lead.facebook) {
                const sanitizedFacebook = this.sanitizeUrl(lead.facebook);
                actionsHtml += `<a href="${sanitizedFacebook}" target="_blank" class="kanban-card-btn facebook" title="Facebook Profile" style="background: var(--accent-blue); color: white; border-radius: 4px; padding: 4px 8px; font-size: 0.75rem; font-weight: 600; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; height: 25px;">📘 Page</a>`;
            }
        } else if (lead.id) {
            actionsHtml += `<button class="kanban-card-btn scan-social" onclick="App.scanSocials(${lead.id}, ${idx})" style="font-size: 0.75rem; padding: 4px 8px; background: rgba(0,212,255,0.1); border: 1px solid var(--accent-cyan); color: var(--accent-cyan); border-radius: 4px; cursor: pointer;">🔍 Scan Socials</button>`;
        }
        
        let whatsappBtnHtml = '';
        if (lead.whatsapp_number) {
            if (lead.line_type === 'LANDLINE') {
                whatsappBtnHtml = `<button class="kanban-card-btn whatsapp disabled-landline" title="Landline Number (No WhatsApp)" style="background: rgba(255,255,255,0.05); color: var(--text-muted); border-radius: 4px; padding: 4px 8px; border: 1px solid var(--border-color); font-size: 0.75rem; cursor: not-allowed;" disabled>💬 Pitch</button>`;
            } else {
                whatsappBtnHtml = `<button class="kanban-card-btn whatsapp" title="Personalized WhatsApp Pitch" onclick="App.openWhatsApp(${idx})" style="background: #25d366; color: white; border-radius: 4px; padding: 4px 8px; border: none; font-size: 0.75rem; font-weight: 600; display: flex; align-items: center; gap: 4px; cursor: pointer;">💬 Pitch</button>`;
            }
        }

        let emailBtnHtml = '';
        if (lead.email) {
            emailBtnHtml = `<button class="kanban-card-btn email" title="Send Email Pitch" onclick="App.openEmail(${idx})" style="background: var(--accent-blue); color: white; border: none; font-size: 0.75rem; padding: 4px 8px; border-radius: 4px; display: inline-flex; align-items: center; gap: 4px; cursor: pointer;">📧 Email</button>`;
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
                    lead.pipeline_stage = newStage;
                    if (newStage === 'PITCHED') {
                        lead.contacted = 1;
                        if (!lead.contact_date) {
                            lead.contact_date = new Date().toISOString();
                        }
                    }
                    
                    UI.renderLeads(AppState.leads);
                    
                    const data = await API.updateLeadPipelineStage(leadId, newStage);
                    if (data.success) {
                        UI.showToast(`Updated "${lead.name}" pipeline stage to ${newStage}!`, 'success');
                    } else {
                        throw new Error(data.error || 'Sync failed');
                    }
                } catch (err) {
                    console.error('Failed to sync Kanban stage:', err);
                    UI.showToast(`Stage sync failed: ${err.message}. Reverting...`, 'error');
                    lead.pipeline_stage = oldStage;
                    UI.renderLeads(AppState.leads);
                }
            }, { signal });
        });
    },

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
        
        document.querySelectorAll('.leads-table th').forEach(th => {
            th.classList.remove('sorted-asc', 'sorted-desc');
        });
        
        const clickedTh = document.querySelector(`.leads-table th[data-sort="${column}"]`);
        if (clickedTh) {
            clickedTh.classList.add(`sorted-${AppState.sortDirection}`);
        }
        
        this.renderLeads(AppState.leads);
    },

    showToast(message, type = 'info') {
        const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
        
        let isGeminiError = false;
        if (type === 'error' && message) {
            const msgLower = message.toLowerCase();
            if (msgLower.includes('gemini') || msgLower.includes('ai generation') || msgLower.includes('generativelanguage')) {
                isGeminiError = true;
                // Beautify/clarify Gemini errors for premium feel
                if (msgLower.includes('key not valid') || msgLower.includes('api key not valid') || msgLower.includes('invalid api key') || msgLower.includes('key is invalid') || msgLower.includes('key is missing') || msgLower.includes('key not configured')) {
                    message = "❌ Gemini API Key Error: Your Gemini API key is invalid, missing or expired. Please check/update your key in Settings.";
                } else if (msgLower.includes('quota') || msgLower.includes('rate limit') || msgLower.includes('exhausted') || msgLower.includes('limit exceeded') || msgLower.includes('limit hits')) {
                    message = "⚠️ Gemini API Limit Reached: Your Gemini API key has hit a rate limit or quota limit. Please wait a moment or check your Google AI Studio billing.";
                } else if (msgLower.includes('not enabled') || msgLower.includes('disabled') || msgLower.includes('restricted')) {
                    message = "⚠️ Gemini API Disabled: The Generative Language API is not enabled on this API key. Please enable it in Google Cloud Console or create a new key on Google AI Studio.";
                } else {
                    // Keep the original descriptive error, but strip ugly stack wrappers to make it clean
                    message = message
                        .replace("AI Generation failed: All Gemini models failed. Last error: Exception: ", "")
                        .replace("AI Generation failed: All Gemini models failed. Last error: ", "")
                        .replace("AI Generation failed: Exception: ", "")
                        .replace("AI Generation failed: ", "");
                    message = `🤖 Gemini Error: ${message}`;
                }
                type = 'error';
            }
        }

        if (type === 'error' && !isGeminiError && message && (message.includes('run out of searches') || message.includes('quota') || message.includes('SerpApi Error') || message.includes('SerpApi key') || message.includes('SerpApi Key'))) {
            if (window.IS_ADMIN) {
                message = "⚠️ Master SerpApi key limit has been crossed or it is invalid. Please update the key in the Admin Console.";
            } else {
                message = "⚠️ Server busy or under maintenance... take a while, have a teacup and come back.";
            }
            type = 'error';
        }
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
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
        }, 6000);
    },

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
    },

    sanitizeUrl(url) {
        if (!url) return '#';
        let trimmed = String(url).trim();
        if (trimmed.startsWith('//')) {
            trimmed = 'https:' + trimmed;
        }
        if (/^(https?|ftp):\/\//i.test(trimmed)) {
            return this.escapeHtml(trimmed);
        }
        return '#';
    },

    initTiltEffects() {
        document.body.addEventListener('mousemove', (e) => {
            const card = e.target.closest('.stat-card, .kanban-card');
            if (!card) return;
            
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const tiltX = ((y - centerY) / centerY) * -10;
            const tiltY = ((x - centerX) / centerX) * 10;
            
            if (window.gsap) {
                window.gsap.to(card, {
                    rotateX: tiltX,
                    rotateY: tiltY,
                    transformPerspective: 800,
                    ease: 'power1.out',
                    duration: 0.15,
                    overwrite: 'auto'
                });
            }
        });
        
        document.body.addEventListener('mouseleave', (e) => {
            const card = e.target.closest('.stat-card, .kanban-card');
            if (card) {
                if (window.gsap) {
                    window.gsap.to(card, {
                        rotateX: 0,
                        rotateY: 0,
                        ease: 'power2.out',
                        duration: 0.35,
                        overwrite: 'auto'
                    });
                }
            }
        }, true);
    }
};
