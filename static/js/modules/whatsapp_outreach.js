import { API } from './api.js';
import { AppState } from './state.js';
import { UI } from './ui.js';
import { CryptoHelper } from './crypto.js';

export const whatsappOutreachModule = {
    openWhatsAppCampaign() {
        const leads = AppState.leads || [];
        if (leads.length === 0) {
            UI.showToast('Search results me aisi koi lead nahi hai! Pehle search run karein.', 'warning');
            return;
        }

        const existingIds = new Set((AppState.whatsappCampaignLeads || []).map(l => l.id));
        const leadsChanged = leads.length !== existingIds.size || leads.some(l => !existingIds.has(l.id));

        if (leadsChanged || !AppState.whatsappCampaignLeads || AppState.whatsappCampaignLeads.length === 0) {
            const existingMap = {};
            (AppState.whatsappCampaignLeads || []).forEach(l => { existingMap[l.id] = l; });

            AppState.whatsappCampaignLeads = leads.map(lead => {
                const existing = existingMap[lead.id];
                if (existing && (existing.whatsapp_draft_status === 'ready' || existing.whatsapp_send_status === 'sent')) {
                    return { ...lead, ...existing, name: lead.name, phone: (lead.phone || lead.whatsapp_number) || existing.phone };
                }
                return {
                    ...lead,
                    whatsapp_phone_status: (lead.phone || lead.whatsapp_number) ? 'found' : 'missing',
                    whatsapp_draft_status: 'not-drafted',
                    whatsapp_send_status: 'pending',
                    whatsapp_body: ''
                };
            });
        }

        AppState.selectedWhatsAppCampaignLeadId = AppState.selectedWhatsAppCampaignLeadId || null;

        this.renderWhatsAppCampaignList();
        this.updateWhatsAppCampaignStats();
        
        if (UI.el.whatsappCampaignOutboxWorkspace) UI.el.whatsappCampaignOutboxWorkspace.style.display = 'none';
        if (UI.el.whatsappCampaignOutboxEmptyState) UI.el.whatsappCampaignOutboxEmptyState.style.display = 'flex';
        if (UI.el.whatsappCampaignProgressContainer) UI.el.whatsappCampaignProgressContainer.style.display = 'none';

        UI.openModal('whatsappCampaignModal');
    },

    updateWhatsAppCampaignStats() {
        const leads = AppState.whatsappCampaignLeads || [];
        const total = leads.length;
        const phones = leads.filter(l => (l.phone || l.whatsapp_number) || l.whatsapp_phone_status === 'found').length;
        const drafts = leads.filter(l => l.whatsapp_draft_status === 'ready').length;
        const sent = leads.filter(l => l.whatsapp_send_status === 'sent').length;

        if (UI.el.whatsappCampaignStatLeads) UI.el.whatsappCampaignStatLeads.textContent = total;
        if (UI.el.whatsappCampaignStatEmails) UI.el.whatsappCampaignStatEmails.textContent = phones; // Reusing this ID since Python replace mapped it
        if (UI.el.whatsappCampaignStatDrafts) UI.el.whatsappCampaignStatDrafts.textContent = drafts;
        if (UI.el.whatsappCampaignStatSent) UI.el.whatsappCampaignStatSent.textContent = sent;
    },

    renderWhatsAppCampaignList() {
        const body = UI.el.whatsappCampaignTableBody;
        if (!body) return;

        const leads = AppState.whatsappCampaignLeads || [];
        
        body.innerHTML = leads.map((lead, index) => {
            const activeClass = lead.id === AppState.selectedWhatsAppCampaignLeadId ? 'active' : '';
            const safeName = UI.escapeHtml(lead.name);
            
            let phoneHtml = '';
            const thePhone = lead.phone || lead.whatsapp_number;
            if (thePhone) {
                phoneHtml = `
                    <div class="campaign-card-email-box">
                        <span style="font-size: 0.72rem;">📱</span>
                        <span class="campaign-card-email-text">${UI.escapeHtml(thePhone)}</span>
                    </div>
                `;
            } else {
                phoneHtml = `
                    <div style="display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0;">
                        <div class="campaign-card-email-box missing">
                            <span style="color: var(--text-muted); font-size: 0.72rem;">No Phone</span>
                        </div>
                    </div>
                `;
            }

            let draftBadge = '';
            if (lead.whatsapp_reply_received || lead.whatsapp_send_status === 'replied') draftBadge = `<span class="campaign-status-badge delivered" style="background: var(--success); color: white;">Replied & Pitched 🚀</span>`;
            else if (lead.whatsapp_sent || lead.whatsapp_send_status === 'sent') draftBadge = `<span class="campaign-status-badge delivered">Icebreaker Sent ✅</span>`;
            else if (lead.whatsapp_send_status === 'failed') draftBadge = `<span class="campaign-status-badge failed">Failed ❌</span>`;
            else if (lead.whatsapp_draft_status === 'ready') draftBadge = `<span class="campaign-status-badge draft-ready">Draft Ready 🟢</span>`;

            return `
                <div class="campaign-lead-card ${activeClass}" onclick="App.selectWhatsAppCampaignLead(${lead.id})">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                        <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-primary); text-transform: capitalize; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 140px;" title="${safeName}">
                            ${safeName}
                        </div>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 6px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
                            ${phoneHtml}
                            ${draftBadge}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    },

    selectWhatsAppCampaignLead(leadId) {
        const lead = (AppState.whatsappCampaignLeads || []).find(l => l.id === leadId);
        if (!lead) return;

        AppState.selectedWhatsAppCampaignLeadId = leadId;
        this.renderWhatsAppCampaignList();

        if (UI.el.whatsappCampaignOutboxEmptyState) UI.el.whatsappCampaignOutboxEmptyState.style.display = 'none';
        if (UI.el.whatsappCampaignOutboxWorkspace) UI.el.whatsappCampaignOutboxWorkspace.style.display = 'flex';

        if (UI.el.whatsappCampaignSelectedName) UI.el.whatsappCampaignSelectedName.textContent = lead.name;
        if (UI.el.whatsappCampaignSelectedEmail) UI.el.whatsappCampaignSelectedEmail.textContent = (lead.phone || lead.whatsapp_number) || 'No Phone Number';
        
        if (UI.el.whatsappCampaignBodyInput) {
            UI.el.whatsappCampaignBodyInput.value = lead.whatsapp_body || '';
            UI.el.whatsappCampaignBodyInput.oninput = () => this.updateWhatsAppLivePreview();
        }
        
        if (UI.el.whatsappPreviewBusinessName) UI.el.whatsappPreviewBusinessName.textContent = lead.name;
        if (UI.el.whatsappPreviewDeveloperBrand) UI.el.whatsappPreviewDeveloperBrand.textContent = localStorage.getItem('sender_brand') || 'Our Agency';

        this.updateWhatsAppLivePreview();
    },

    updateWhatsAppLivePreview() {
        if (!UI.el.whatsappCampaignBodyInput || !UI.el.whatsappCampaignVisualPreview) return;
        const bodyText = UI.el.whatsappCampaignBodyInput.value || '';
        
        if (!bodyText.trim()) {
            UI.el.whatsappCampaignVisualPreview.innerHTML = '<span style="color: #94a3b8; font-style: italic;">Draft your WhatsApp message or click "Draft AI" to see preview...</span>';
            return;
        }

        UI.el.whatsappCampaignVisualPreview.textContent = bodyText;
    },

    async generateWhatsAppCampaignDrafts() {
        const leads = AppState.whatsappCampaignLeads || [];
        const eligibleLeads = leads.filter(l => (l.phone || l.whatsapp_number) && l.whatsapp_draft_status !== 'ready');
        
        if (eligibleLeads.length === 0) {
            UI.showToast('No leads with phone numbers to draft for, or all drafts are already ready!', 'info');
            return;
        }

        const geminiKeyRaw = localStorage.getItem('gemini_api_key');
        const geminiKey = geminiKeyRaw ? await CryptoHelper.decrypt(geminiKeyRaw, AppState.encryptionKey) : '';
        
        if (!geminiKey) {
            UI.showToast('Please configure your Gemini API Key in Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const tone = UI.el.whatsappCampaignToneSelect?.value || 'elite';
        const language = UI.el.whatsappCampaignLanguageSelect?.value || 'hinglish';
        let service = UI.el.whatsappCampaignServiceSelect?.value || 'web_design';

        const container = UI.el.whatsappCampaignProgressContainer;
        const label = UI.el.whatsappCampaignProgressLabel;
        const bar = UI.el.whatsappCampaignProgressBar;
        const percentage = UI.el.whatsappCampaignProgressPercentage;

        if (container) container.style.display = 'block';

        let processed = 0;
        for (const lead of eligibleLeads) {
            if (label) label.textContent = `Drafting WhatsApp AI for "${lead.name}" (${processed + 1}/${eligibleLeads.length})...`;
            
            try {
                const data = await API.request('/api/outreach/generate-whatsapp', {
                    method: 'POST',
                    headers: { 'X-Gemini-API-Key': geminiKey },
                    body: JSON.stringify({
                        lead: lead,
                        tone: tone,
                        service: service,
                        language: language,
                        sender: {
                            name: localStorage.getItem('sender_name') || '',
                            brand: localStorage.getItem('sender_brand') || '',
                            role: localStorage.getItem('sender_role') || ''
                        }
                    })
                });

                if (data.success) {
                    lead.whatsapp_body = data.message || '';
                    lead.whatsapp_draft_status = 'ready';
                    if (AppState.selectedWhatsAppCampaignLeadId === lead.id) {
                        this.selectWhatsAppCampaignLead(lead.id);
                    }
                }
            } catch (err) {
                console.error(`WhatsApp AI generation failed for ${lead.name}:`, err);
            }

            processed++;
            const pct = Math.round((processed / eligibleLeads.length) * 100);
            if (percentage) percentage.textContent = `${pct}%`;
            if (bar) bar.style.width = `${pct}%`;
            
            this.renderWhatsAppCampaignList();
            this.updateWhatsAppCampaignStats();
            
            await new Promise(resolve => setTimeout(resolve, 200));
        }

        UI.showToast(`Drafted ${processed} WhatsApp messages!`, 'success');
        setTimeout(() => { if (container) container.style.display = 'none'; }, 2000);
    },

    async dispatchBulkWhatsApp() {
        const leads = AppState.whatsappCampaignLeads || [];
        const sendableLeads = leads.filter(l => l.whatsapp_draft_status === 'ready' && l.whatsapp_send_status !== 'sent');

        if (sendableLeads.length === 0) {
            UI.showToast('No ready drafts to send!', 'warning');
            return;
        }

        const waToken = localStorage.getItem('whatsapp_token');
        const waPhoneId = localStorage.getItem('whatsapp_phone_id');
        
        if (!waToken || !waPhoneId) {
            UI.showToast('Please configure WhatsApp API Token and Phone ID in settings.', 'error');
            return;
        }

        const confirmed = await UI.showConfirm(
            "Send WhatsApp Campaign",
            `🚀 Dispatching ${sendableLeads.length} WhatsApp Icebreaker Templates via Meta Cloud API.\nAre you sure you want to proceed?`,
            "📱"
        );
        if (!confirmed) return;

        const container = UI.el.whatsappCampaignProgressContainer;
        const label = UI.el.whatsappCampaignProgressLabel;
        const bar = UI.el.whatsappCampaignProgressBar;
        const percentage = UI.el.whatsappCampaignProgressPercentage;

        if (container) container.style.display = 'block';
        
        let processed = 0;
        for (const lead of sendableLeads) {
            lead.whatsapp_send_status = 'sending';
            this.renderWhatsAppCampaignList();

            if (label) label.textContent = `Sending Icebreaker to "${lead.name}" (${processed + 1}/${sendableLeads.length})...`;

            try {
                const res = await API.request('/api/outreach/send-whatsapp', {
                    method: 'POST',
                    headers: {
                        'X-WhatsApp-Token': waToken,
                        'X-WhatsApp-Phone-ID': waPhoneId
                    },
                    body: JSON.stringify({
                        lead_id: lead.id,
                        phone: lead.phone || lead.whatsapp_number,
                        template_name: 'icebreaker_hello'
                    })
                });

                if (res.success) {
                    lead.whatsapp_send_status = 'sent';
                } else {
                    lead.whatsapp_send_status = 'failed';
                }
            } catch (err) {
                lead.whatsapp_send_status = 'failed';
            }

            processed++;
            const pct = Math.round((processed / sendableLeads.length) * 100);
            if (percentage) percentage.textContent = `${pct}%`;
            if (bar) bar.style.width = `${pct}%`;
            
            this.renderWhatsAppCampaignList();
            this.updateWhatsAppCampaignStats();

            // Rate limiting pause
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        const successCount = sendableLeads.filter(l => l.whatsapp_send_status === 'sent').length;
        UI.showToast(`WhatsApp Campaign finished! Delivered: ${successCount}`, 'success');
        setTimeout(() => { if (container) container.style.display = 'none'; }, 3000);
    }
};
