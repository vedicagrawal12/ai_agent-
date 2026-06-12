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
            if (lead.id) {
                const senderName = localStorage.getItem('sender_name') || '';
                const senderBrand = localStorage.getItem('sender_brand') || '';
                const previewUrl = `/preview/${lead.id}?sender_name=${encodeURIComponent(senderName)}&sender_brand=${encodeURIComponent(senderBrand)}`;
                mockupIframe.src = previewUrl;
            } else {
                mockupIframe.src = 'about:blank';
            }
        }

        const detailPane = document.getElementById('detailPane');
        if (detailPane) {
            detailPane.classList.add('active');
            if (window.gsap) {
                if (window.innerWidth < 1024) {
                    window.gsap.to(detailPane, { y: 0, x: 0, duration: 0.45, ease: 'power2.out', overwrite: 'auto' });
                } else {
                    window.gsap.to(detailPane, { x: 0, y: 0, duration: 0.45, ease: 'power2.out', overwrite: 'auto' });
                }
            }
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

        if (!confirm(`Kya aap sabhi ${leadsToScan.length} leads ke socials scan karna chahte hain?\n\nIs bulk operation se aapke SerpApi search credits consume honge (har lead ke liye 1 search credit).`)) {
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
    }
};
