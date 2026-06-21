/**
 * LeadHunter AI — Leads Management Module
 */

import { API } from './api.js';
import { UI } from './ui.js';
import { AppState } from './state.js';
import { outreachModule } from './outreach.js';

export const leadsModule = {
    handleRowClick(event, index) {
        if (event.target.closest('a') || event.target.closest('button')) {
            return;
        }
        const lead = AppState.leads[index];
        if (lead) {
            this.selectLead(lead.id);
            this.switchDetailTab('whatsapp'); // Default to WhatsApp pitch tab
        }
    },

    selectLead(leadId) {
        const lead = AppState.leads.find(l => l.id === leadId) || AppState.leads.find(l => l.place_id === leadId);
        if (!lead) return;

        AppState.currentWhatsAppLead = lead;
        AppState.currentEmailLead = lead;
        AppState.selectedLead = lead;

        const detailBusinessName = document.getElementById('detailBusinessName');
        const detailBusinessCategory = document.getElementById('detailBusinessCategory');
        if (detailBusinessName) detailBusinessName.textContent = lead.name;
        if (detailBusinessCategory) detailBusinessCategory.textContent = lead.category || 'Local Business';

        const waBizName = document.getElementById('whatsappBusinessName');
        const waPhoneNum = document.getElementById('whatsappPhoneNumber');
        if (waBizName) waBizName.textContent = lead.name;
        if (waPhoneNum) waPhoneNum.textContent = lead.phone || lead.whatsapp_number || 'N/A';

        if (UI.el.emailBusinessName) UI.el.emailBusinessName.textContent = lead.name;
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

        const mockupIframe = document.getElementById('mockupIframe');
        if (mockupIframe) {
            if (lead.id !== undefined && lead.id !== null && lead.id !== '') {
                const senderName = localStorage.getItem('sender_name') || '';
                const senderBrand = localStorage.getItem('sender_brand') || '';
                const previewUrl = `/preview/${lead.id}?sender_name=${encodeURIComponent(senderName)}&sender_brand=${encodeURIComponent(senderBrand)}`;
                mockupIframe.src = previewUrl;
            } else {
                mockupIframe.src = 'about:blank';
            }
        }

        // Initialize WhatsApp Tab Defaults
        if (UI.el.pitchServiceSelect) {
            const hasNoSite = !lead.website || !lead.website.trim();
            const isBroken = !!lead.is_broken_website;
            if (hasNoSite || isBroken) {
                UI.el.pitchServiceSelect.value = 'web_design';
            } else {
                UI.el.pitchServiceSelect.value = 'seo';
            }
            if (UI.el.pitchCustomServiceContainer) UI.el.pitchCustomServiceContainer.style.display = 'none';
        }
        const customMessageInput = document.getElementById('customMessageInput');
        const customArea = document.getElementById('customMessageArea');
        if (lead.custom_pitch) {
            if (customMessageInput) customMessageInput.value = lead.custom_pitch;
        } else {
            if (customMessageInput) customMessageInput.value = '';
        }
        if (customArea) customArea.style.display = 'none';

        // Initialize Social DM Tab Defaults
        const socialBusinessName = document.getElementById('socialBusinessName');
        const socialCoordinates = document.getElementById('socialCoordinates');
        if (socialBusinessName) socialBusinessName.textContent = lead.name;
        
        let socialLinksText = [];
        if (lead.instagram) socialLinksText.push('Instagram (Available)');
        if (lead.facebook) socialLinksText.push('Facebook (Available)');
        
        if (socialCoordinates) {
            if (socialLinksText.length > 0) {
                socialCoordinates.textContent = socialLinksText.join(' / ');
                socialCoordinates.style.color = 'var(--accent-cyan)';
            } else {
                socialCoordinates.textContent = 'No socials scanned yet.';
                socialCoordinates.style.color = 'var(--accent-red)';
            }
        }

        const customSocialMessageInput = document.getElementById('customSocialMessageInput');
        const customSocialArea = document.getElementById('customSocialMessageArea');
        const socialMessagePreview = document.getElementById('socialMessagePreview');
        if (customSocialMessageInput) customSocialMessageInput.value = '';
        if (customSocialArea) customSocialArea.style.display = 'none';
        if (socialMessagePreview) socialMessagePreview.textContent = 'Click generate to create a custom social media pitch...';
        
        if (UI.el.socialServiceSelect) {
            UI.el.socialServiceSelect.value = 'social_media';
            if (UI.el.socialCustomServiceContainer) UI.el.socialCustomServiceContainer.style.display = 'none';
        }

        // Initialize Email Tab Defaults
        if (UI.el.emailSubjectInput) UI.el.emailSubjectInput.value = '';
        if (UI.el.emailBodyInput) UI.el.emailBodyInput.value = '';

        if (UI.el.emailServiceSelect) {
            const hasNoSite = !lead.website || !lead.website.trim();
            const isBroken = !!lead.is_broken_website;
            if (hasNoSite || isBroken) {
                UI.el.emailServiceSelect.value = 'web_design';
            } else {
                UI.el.emailServiceSelect.value = 'seo';
            }
            if (UI.el.emailCustomServiceContainer) UI.el.emailCustomServiceContainer.style.display = 'none';
        }

        // Initialize radio selections and message preview
        setTimeout(() => {
            const firstRadio = document.querySelector('input[name="template"]:not([value="custom"])') || document.querySelector('input[name="template"]');
            if (firstRadio) {
                firstRadio.checked = true;
                AppState.selectedTemplate = firstRadio.value;
                const container = UI.el.templateOptions;
                if (container) {
                    container.querySelectorAll('.template-option').forEach(o => o.classList.remove('selected'));
                    firstRadio.closest('.template-option')?.classList.add('selected');
                }
            }
            if (outreachModule && typeof outreachModule.updateMessagePreview === 'function') {
                outreachModule.updateMessagePreview();
            }
        }, 50);

        // Populate SEO Audit Section
        const seoSection = document.getElementById('detailSEOAuditSection');
        if (seoSection) {
            const hasWebsite = lead.website && lead.website.trim() !== '';
            let auditHtml = '';

            if (!hasWebsite) {
                auditHtml = `
                    <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; width: 100%;">
                        <span style="font-size: 0.85rem; color: var(--text-secondary);">🔍 No website URL found for this business.</span>
                    </div>
                `;
            } else {
                let auditData = null;
                if (lead.audit_data) {
                    try {
                        auditData = typeof lead.audit_data === 'string' ? JSON.parse(lead.audit_data) : lead.audit_data;
                    } catch (e) {
                        console.error('Error parsing audit_data:', e);
                    }
                }

                if (auditData && auditData.overall_score !== undefined) {
                    const score = auditData.overall_score;
                    let scoreColor = 'var(--accent-red)';
                    if (score >= 80) {
                        scoreColor = 'var(--accent-green)';
                    } else if (score >= 50) {
                        scoreColor = 'var(--accent-orange)';
                    }

                    const auditLink = `/audit/${lead.id}`;

                    auditHtml = `
                        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; width: 100%;">
                            <div>
                                <div style="font-size: 0.8rem; color: var(--text-secondary); display: flex; align-items: center; gap: 6px;">
                                    <span>🔍 Website Audit Score:</span>
                                    <strong style="color: ${scoreColor}; font-size: 0.95rem;">${score}/100</strong>
                                </div>
                                <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px;">
                                    Audited on: ${auditData.audited_at || 'Recently'}
                                </div>
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <a href="${auditLink}" target="_blank" class="btn btn-secondary btn-sm" style="font-size: 0.75rem; padding: 6px 10px; border: 1px solid var(--accent-cyan); color: var(--accent-cyan); text-decoration: none; border-radius: var(--radius-sm); font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
                                    📄 Report Card
                                </a>
                                <button id="copyAuditReportLinkBtn" class="btn btn-secondary btn-sm" style="font-size: 0.75rem; padding: 6px 10px; border: 1px solid var(--accent-cyan); color: var(--accent-cyan); background: transparent; border-radius: var(--radius-sm); font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;">
                                    📋 Copy URL
                                </button>
                                <button id="runWebsiteAuditBtn" class="btn btn-secondary btn-sm" style="font-size: 0.75rem; padding: 6px 6px; border: 1px solid var(--border-color); color: var(--text-muted); background: transparent; border-radius: var(--radius-sm); cursor: pointer;" title="Re-run Audit">
                                    🔄
                                </button>
                            </div>
                        </div>
                    `;
                } else {
                    auditHtml = `
                        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; width: 100%;">
                            <div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary);">🔍 Website not audited yet.</div>
                                <div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 2px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${lead.website}">${lead.website}</div>
                            </div>
                            <button id="runWebsiteAuditBtn" class="btn btn-primary btn-sm" style="font-size: 0.8rem; padding: 8px 14px; background: var(--accent-blue); color: white; border: none; border-radius: var(--radius-sm); font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
                                ⚡ Generate SEO Audit Score
                            </button>
                        </div>
                    `;
                }
            }

            seoSection.innerHTML = auditHtml;

            // Bind click handlers
            const runAuditBtn = document.getElementById('runWebsiteAuditBtn');
            if (runAuditBtn) {
                runAuditBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    await this.runWebsiteAudit(lead.id);
                });
            }

            const copyReportLinkBtn = document.getElementById('copyAuditReportLinkBtn');
            if (copyReportLinkBtn) {
                copyReportLinkBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.copyAuditReportLink(lead.id);
                });
            }
        }

        if (lead.id !== undefined && lead.id !== null && lead.id !== '') {
            this.loadOutreachLogs(lead.id);
            this.loadCompetitors(lead.id);
        } else {
            const containers = document.querySelectorAll('#detailPane .outreach-history-list');
            containers.forEach(el => {
                el.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-secondary);">No outreach history (unsaved lead).</div>';
            });
            const tableBody = document.getElementById('dashboardCompetitorTableBody');
            if (tableBody) {
                tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: var(--text-secondary);">Save the lead to generate competitor benchmarks.</td></tr>';
            }
        }

        const detailPane = document.getElementById('detailPane');
        const backdrop = document.getElementById('detailPaneBackdrop');
        if (detailPane) {
            detailPane.classList.add('active');
            if (backdrop) backdrop.classList.add('active');
            
            if (window.gsap) {
                if (window.innerWidth < 1024) {
                    window.gsap.set(detailPane, { xPercent: 0, yPercent: 100, x: 0, y: 0, scale: 1, opacity: 1 });
                    window.gsap.to(detailPane, { yPercent: 0, duration: 0.45, ease: 'power2.out', overwrite: 'auto' });
                } else {
                    window.gsap.set(detailPane, { xPercent: -50, yPercent: -50, x: 0, y: 0, scale: 0.9, opacity: 0 });
                    window.gsap.to(detailPane, { 
                        xPercent: -50,
                        yPercent: -50,
                        scale: 1, 
                        opacity: 1, 
                        duration: 0.4, 
                        ease: 'back.out(1.5)', 
                        overwrite: 'auto' 
                    });
                }
                if (backdrop) {
                    window.gsap.set(backdrop, { opacity: 0 });
                    window.gsap.to(backdrop, { opacity: 1, duration: 0.3, overwrite: 'auto' });
                }
            }
        }
    },

    async loadOutreachLogs(leadId) {
        const waContainer = document.getElementById('whatsappHistoryList');
        const emailContainer = document.getElementById('emailHistoryList');
        
        if (waContainer) waContainer.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-secondary);">Loading history...</div>';
        if (emailContainer) emailContainer.innerHTML = '<div style="font-size: 0.8rem; color: var(--text-secondary);">Loading history...</div>';

        try {
            const data = await API.request(`/api/leads/${leadId}/outreach-logs`, {
                method: 'GET'
            });

            let waHtml = '';
            let emailHtml = '';

            if (data && data.length > 0) {
                data.forEach(log => {
                    const sentAt = new Date(log.sent_at).toLocaleString();
                    const isEmail = log.template_used === 'cold_email';
                    const icon = isEmail ? '📧' : '📱';
                    const channel = isEmail ? 'Email' : 'WhatsApp';

                    let trackingInfo = '';
                    if (isEmail) {
                        const openedText = log.opened ? `🟢 Opened (${log.open_count}x)` : '⚪ Unopened';
                        const clickedText = log.clicked ? `🟢 Clicked (${log.click_count}x)` : '⚪ Unclicked';
                        trackingInfo = `<div style="font-size: 0.72rem; display: flex; gap: 8px; margin-top: 4px;">
                            <span style="color: ${log.opened ? 'var(--accent-green)' : 'var(--text-muted)'};">${openedText}</span>
                            <span style="color: ${log.clicked ? 'var(--accent-green)' : 'var(--text-muted)'};">${clickedText}</span>
                        </div>`;
                    }

                    const itemHtml = `
                        <div style="padding: 8px; background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: var(--radius-sm); font-size: 0.8rem; margin-bottom: 6px; text-align: left;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                                <strong>${icon} ${channel}</strong>
                                <span style="font-size: 0.7rem; color: var(--text-muted);">${sentAt}</span>
                            </div>
                            <div style="font-size: 0.75rem; color: var(--text-secondary); text-overflow: ellipsis; overflow: hidden; white-space: nowrap; max-width: 250px;" title="${log.message_sent}">
                                ${log.message_sent}
                            </div>
                            ${trackingInfo}
                        </div>
                    `;

                    if (isEmail) {
                        emailHtml += itemHtml;
                    } else {
                        waHtml += itemHtml;
                    }
                });
            }

            if (!waHtml) waHtml = '<div style="font-size: 0.8rem; color: var(--text-secondary);">No WhatsApp outreach history.</div>';
            if (!emailHtml) emailHtml = '<div style="font-size: 0.8rem; color: var(--text-secondary);">No email outreach history.</div>';

            if (waContainer) waContainer.innerHTML = waHtml;
            if (emailContainer) emailContainer.innerHTML = emailHtml;
        } catch (error) {
            console.error('Error fetching outreach logs:', error);
            const errHtml = '<div style="font-size: 0.8rem; color: var(--accent-red);">Failed to load history.</div>';
            if (waContainer) waContainer.innerHTML = errHtml;
            if (emailContainer) emailContainer.innerHTML = errHtml;
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
                AppState.leads[index].instagram = data.instagram || '';
                AppState.leads[index].facebook = data.facebook || '';

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

        let message = '';
        if (lead.custom_pitch) {
            message = lead.custom_pitch;
        } else {
            const templateData = AppState.whatsappTemplates['website_pitch'];
            message = templateData ? templateData.message : 'Hello {business_name}!';
        }

        const projectSampleText = outreachModule.getBestPortfolioProjectSample(lead);
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
            await navigator.clipboard.writeText(message);
            UI.showToast('📋 Pitch copied to clipboard! Opening Instagram...', 'success');
        } catch (clipErr) {
            const textArea = document.createElement('textarea');
            textArea.value = message;
            document.body.appendChild(textArea);
            textArea.select();
            // Deprecated copy fallback for older browsers
            document.execCommand('copy');
            document.body.removeChild(textArea);
            UI.showToast('📋 Pitch copied to clipboard! Opening Instagram...', 'success');
        }

        setTimeout(() => {
            const sanitizedInstagram = UI.sanitizeUrl(lead.instagram);
            if (sanitizedInstagram !== '#') {
                window.open(sanitizedInstagram, '_blank');
            }
        }, 800);
    },

    copyPhone(index) {
        const lead = AppState.leads[index];
        if (!lead || !lead.phone) {
            UI.showToast('No phone number available', 'error');
            return;
        }

        navigator.clipboard.writeText(lead.phone).then(() => {
            UI.showToast(`Copied: ${lead.phone}`, 'success');
        }).catch(() => {
            const textArea = document.createElement('textarea');
            textArea.value = lead.phone;
            document.body.appendChild(textArea);
            textArea.select();
            // Deprecated copy fallback for older browsers
            document.execCommand('copy');
            document.body.removeChild(textArea);
            UI.showToast(`Copied: ${lead.phone}`, 'success');
        });
    },

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
            const textArea = document.createElement('textarea');
            textArea.value = url;
            document.body.appendChild(textArea);
            textArea.select();
            // Deprecated copy fallback for older browsers
            document.execCommand('copy');
            document.body.removeChild(textArea);
            UI.showToast('🚀 Mockup Link copied to clipboard! Ready to share!', 'success');
        });
    },

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

    async handleBulkScanSocials() {
        if (AppState.leads.length === 0) {
            UI.showToast('Bulk scan ke liye table mein leads hona zaroori hai!', 'error');
            return;
        }

        UI.el.bulkScanSocialsBtn.disabled = true;

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

        const confirmed = await UI.showConfirm(
            "Bulk Social Scan",
            `Kya aap sabhi ${leadsToScan.length} leads ke socials scan karna chahte hain?\n\nIs bulk operation se aapke search credits consume honge (har lead ke liye 1 search credit).`,
            "🔍"
        );
        if (!confirmed) {
            UI.el.bulkScanSocialsBtn.disabled = false;
            UI.el.bulkProgressBanner.style.display = 'none';
            return;
        }

        let completed = 0;
        const total = leadsToScan.length;

        for (const lead of leadsToScan) {
            try {
                const idx = AppState.leads.findIndex(l => l.id === lead.id);
                if (idx === -1) continue;

                const socialCell = document.querySelector(`#leadsTableBody tr[data-lead-id="${lead.id}"] td:nth-child(9)`);
                if (socialCell) {
                    socialCell.innerHTML = '<span style="font-size: 0.85rem; color: var(--accent-cyan); animation: pulse 1s infinite;">⏳ Scanning...</span>';
                }

                UI.el.bulkProgressLabel.textContent = `Scanning socials for "${lead.name}" (${completed + 1}/${total})...`;

                const data = await API.request(`/api/leads/${lead.id}/scan-socials`, {
                    method: 'POST'
                });

                if (data.success) {
                    lead.instagram = data.instagram;
                    lead.facebook = data.facebook;

                    if (socialCell) {
                        let links = [];
                        if (data.instagram) {
                            const sanitizedInstagram = UI.sanitizeUrl(data.instagram);
                            links.push(`<a href="${sanitizedInstagram}" target="_blank" class="social-icon instagram" title="Instagram">📸</a>`);
                        }
                        if (data.facebook) {
                            const sanitizedFacebook = UI.sanitizeUrl(data.facebook);
                            links.push(`<a href="${sanitizedFacebook}" target="_blank" class="social-icon facebook" title="Facebook">👥</a>`);
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

    async runWebsiteAudit(leadId) {
        const btn = document.getElementById('runWebsiteAuditBtn');
        const originalHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.innerHTML = '⏳ Auditing...';
            btn.disabled = true;
        }

        try {
            const data = await API.request(`/api/leads/${leadId}/audit`, {
                method: 'POST'
            });

            if (data.success && data.audit_data) {
                // Update the lead in AppState
                const index = AppState.leads.findIndex(l => l.id === leadId);
                if (index !== -1) {
                    AppState.leads[index].audit_data = JSON.stringify(data.audit_data);
                }

                // Refresh detail pane and list
                this.selectLead(leadId);
                UI.renderLeads(AppState.leads);
                UI.showToast('✨ SEO and Performance Audit completed successfully!', 'success');
            } else {
                UI.showToast(data.error || 'Audit execution failed.', 'error');
            }
        } catch (error) {
            UI.showToast('Audit failed: ' + error.message, 'error');
        } finally {
            if (btn) {
                btn.innerHTML = originalHtml;
                btn.disabled = false;
            }
        }
    },

    copyAuditReportLink(leadId) {
        const absoluteUrl = `${window.location.origin}/audit/${leadId}`;
        navigator.clipboard.writeText(absoluteUrl).then(() => {
            UI.showToast('📋 Audit report card link copied to clipboard!', 'success');
        }).catch((err) => {
            console.error('Failed to copy to clipboard:', err);
            // Fallback copy method
            const textArea = document.createElement('textarea');
            textArea.value = absoluteUrl;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            UI.showToast('📋 Audit report card link copied to clipboard!', 'success');
        });
    },

    async loadCompetitors(leadId) {
        const tableBody = document.getElementById('dashboardCompetitorTableBody');
        if (!tableBody) return;
        
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: var(--text-secondary);">⏳ Loading competitor metrics...</td></tr>';
        
        try {
            const data = await API.request(`/api/leads/${leadId}/competitors`, {
                method: 'GET'
            });
            
            if (!data || !data.competitors) {
                tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: var(--text-secondary);">No competitor metrics available.</td></tr>';
                return;
            }
            
            let html = '';
            
            // Helper: get color for a score value (green >= 80, orange >= 50, red < 50, neutral if 0/unaudited)
            const scoreColor = (score, isAudited) => {
                if (!isAudited || score === 0) return 'var(--text-secondary)';
                if (score >= 80) return 'var(--accent-green)';
                if (score >= 50) return 'var(--accent-orange)';
                return 'var(--accent-red)';
            };
            
            // First render the lead itself
            const l = data.lead;
            const lAudited = (l.speed_score !== undefined && l.speed_score !== 0) || (l.seo_score !== undefined && l.seo_score !== 0);
            const lSpeed = lAudited && l.speed_score ? `${l.speed_score}/100` : 'Not Audited';
            const lSeo = lAudited && l.seo_score ? `${l.seo_score}/100` : 'Not Audited';
            const lSsl = l.ssl_score !== undefined ? (l.ssl_score > 0 ? '🟢 Yes' : '🔴 No') : 'Not Audited';
            const lMobile = l.mobile_score !== undefined ? (l.mobile_score > 0 ? '🟢 Yes' : '🔴 No') : 'Not Audited';
            const lRating = l.rating ? l.rating.toFixed(1) : 'N/A';
            const lReviews = l.reviews !== undefined ? l.reviews : 'N/A';
            
            html += `
                <tr class="highlight-row">
                    <td>
                        <span class="matrix-badge you">YOU</span>
                        <strong>${l.name}</strong>
                    </td>
                    <td style="color: ${scoreColor(l.seo_score, lAudited)};">${lSeo}</td>
                    <td style="color: ${scoreColor(l.speed_score, lAudited)};">${lSpeed}</td>
                    <td>⭐ ${lRating}</td>
                    <td>${lReviews}</td>
                    <td>${lSsl}</td>
                    <td>${lMobile}</td>
                </tr>
            `;
            
            // Next render the competitors
            data.competitors.forEach(c => {
                const cSpeed = `${c.speed_score}/100`;
                const cSeo = `${c.seo_score}/100`;
                const cSsl = c.ssl_score > 0 ? '🟢 Yes' : '🔴 No';
                const cMobile = c.mobile_score > 0 ? '🟢 Yes' : '🔴 No';
                const cRating = c.rating ? c.rating.toFixed(1) : 'N/A';
                const cReviews = c.reviews !== undefined ? c.reviews : 'N/A';
                const badgeText = c.is_mock ? 'LOCAL' : 'COMP';
                const cSeoColor = scoreColor(c.seo_score, true);
                const cSpeedColor = scoreColor(c.speed_score, true);
                
                html += `
                    <tr class="competitor-row">
                        <td>
                            <span class="matrix-badge comp">${badgeText}</span>
                            <span>${c.name}</span>
                        </td>
                        <td style="color: ${cSeoColor}; font-weight: 600;">${cSeo}</td>
                        <td style="color: ${cSpeedColor}; font-weight: 600;">${cSpeed}</td>
                        <td>⭐ ${cRating}</td>
                        <td>${cReviews}</td>
                        <td>${cSsl}</td>
                        <td>${cMobile}</td>
                    </tr>
                `;
            });
            
            tableBody.innerHTML = html;
        } catch (error) {
            console.error('Error fetching competitor benchmark data:', error);
            tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 20px; color: var(--accent-red);">Failed to load competitor metrics.</td></tr>';
        }
    }
};
