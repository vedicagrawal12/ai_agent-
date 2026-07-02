/**
 * LeadHunter AI — Outreach Module
 */

import { API } from './api.js';
import { UI } from './ui.js';
import { AppState } from './state.js';
import { CryptoHelper } from './crypto.js';

export const outreachModule = {
    getDefaultSubject() {
        const service = UI.el.campaignServiceSelect?.value || UI.el.emailServiceSelect?.value || 'web_design';
        const subjectMap = {
            'web_design': 'Digital Storefront Design Proposal',
            'seo': 'SEO & Google Ranking Growth Proposal',
            'social_media': 'Social Media Branding Proposal',
            'gmb': 'Google Business Profile Optimization Proposal'
        };
        return subjectMap[service] || 'Business Growth & Digital Services Proposal';
    },

    openWhatsApp(indexOrLead) {
        const lead = typeof indexOrLead === 'object' ? indexOrLead : AppState.leads[indexOrLead];
        if (!lead || !lead.whatsapp_number) {
            UI.showToast('No WhatsApp number available for this business', 'error');
            return;
        }
        
        this.selectLead(lead.id);
        this.switchDetailTab('whatsapp');

        if (UI.el.pitchServiceSelect) {
            const hasNoSite = !lead.website || !lead.website.trim();
            const isBroken = !!lead.is_broken_website;
            if (hasNoSite || isBroken) {
                UI.el.pitchServiceSelect.value = 'web_design';
            } else {
                UI.el.pitchServiceSelect.value = 'seo';
            }
            // Always hide custom service container since we force web_design/seo
            if (UI.el.pitchCustomServiceContainer) UI.el.pitchCustomServiceContainer.style.display = 'none';
        }
        
        const customMessageInput = document.getElementById('customMessageInput');
        const customArea = document.getElementById('customMessageArea');
        
        if (lead.custom_pitch) {
            if (customMessageInput) {
                customMessageInput.value = lead.custom_pitch;
            }
        } else {
            if (customMessageInput) {
                customMessageInput.value = '';
            }
        }

        if (customArea) {
            customArea.style.display = 'none';
        }
        
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
                this.updateMessagePreview();
            }
            if (lead.custom_pitch) {
                UI.showToast('✨ Custom AI Pitch preloaded (select "✏️ Custom Message" to view/use it)', 'info');
            }
        }, 50);
        
        this.updateMessagePreview();
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
            return "hamare dynamic work samples aur website templates ke liye humein contact karein.";
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
        const searchText = `${category} ${name}`;
        
        // Fuzzy keyword map covering 14+ industry verticals
        const categoryKeywordMap = [
            { keywords: ['gym', 'fitness', 'yoga', 'crossfit', 'workout', 'pilates', 'boxing', 'zumba', 'martial'], label: 'Gym/Fitness', projectKeywords: ['gym', 'fitness', 'workout', 'health'] },
            { keywords: ['dentist', 'dental', 'clinic', 'doctor', 'hospital', 'dermatolog', 'physician', 'ortho', 'eye', 'physio', 'chiro', 'ayurved', 'pharma', 'patholog', 'diagnostic'], label: 'Medical/Healthcare', projectKeywords: ['clinic', 'doctor', 'hospital', 'health', 'medical', 'dental', 'care'] },
            { keywords: ['salon', 'spa', 'parlour', 'parlor', 'barber', 'beauty', 'nail', 'hair', 'makeup', 'grooming', 'skincare', 'tattoo', 'mehndi', 'bridal'], label: 'Salon/Beauty', projectKeywords: ['salon', 'beauty', 'spa', 'barber', 'grooming', 'style'] },
            { keywords: ['restaurant', 'cafe', 'hotel', 'bakery', 'bar', 'dhaba', 'food', 'dine', 'dining', 'catering', 'sweet', 'pizza', 'biryani', 'juice', 'tea', 'coffee', 'lounge', 'pub', 'banquet', 'resort', 'prandium'], label: 'Restaurant/Hotel', projectKeywords: ['hotel', 'restaurant', 'cafe', 'food', 'dining', 'prandium', 'bakery', 'catering'] },
            { keywords: ['school', 'coaching', 'tutor', 'academy', 'institute', 'training', 'education', 'college', 'preschool', 'playschool', 'nursery', 'classes', 'learning'], label: 'Education/Coaching', projectKeywords: ['school', 'education', 'academy', 'learning', 'coaching', 'course', 'training'] },
            { keywords: ['garage', 'car wash', 'mechanic', 'automobile', 'auto', 'bike', 'vehicle', 'tyre', 'car dealer', 'showroom', 'service center'], label: 'Automotive', projectKeywords: ['auto', 'car', 'vehicle', 'garage', 'mechanic', 'bike'] },
            { keywords: ['builder', 'property', 'real estate', 'architect', 'interior', 'construction', 'contractor', 'developer', 'flat', 'apartment', 'villa'], label: 'Real Estate', projectKeywords: ['property', 'real estate', 'construction', 'builder', 'architect', 'interior', 'home'] },
            { keywords: ['lawyer', 'advocate', 'legal', 'chartered', 'accountant', 'tax', 'consultant', 'financial', 'insurance', 'loan', 'investment'], label: 'Legal/Finance', projectKeywords: ['lawyer', 'legal', 'finance', 'accounting', 'consulting', 'tax'] },
            { keywords: ['pet ', 'pets', 'veterinary', 'vet ', 'animal', 'dog ', 'dogs', 'puppy', 'kitten', 'kennel', 'aquarium'], label: 'Pet Services', projectKeywords: ['pet', 'vet', 'animal', 'dog'] },
            { keywords: ['shop', 'store', 'boutique', 'electronics', 'furniture', 'jewel', 'clothing', 'garment', 'fashion', 'textile', 'gift', 'handicraft', 'grocery', 'supermarket', 'kirana'], label: 'Retail/Store', projectKeywords: ['shop', 'store', 'ecommerce', 'boutique', 'retail', 'fashion', 'product'] },
            { keywords: ['photographer', 'photography', 'wedding', 'event', 'planner', 'dj', 'decoration', 'florist', 'caterer', 'videograph', 'studio', 'music', 'band'], label: 'Events/Creative', projectKeywords: ['photo', 'wedding', 'event', 'studio', 'portfolio', 'creative', 'film'] },
            { keywords: ['plumber', 'electrician', 'painter', 'pest control', 'ac repair', 'cleaning', 'laundry', 'packers', 'movers', 'carpenter', 'locksmith', 'solar', 'cctv', 'security'], label: 'Home Services', projectKeywords: ['service', 'repair', 'cleaning', 'home', 'maintenance'] },
            { keywords: ['travel', 'tour', 'taxi', 'cab', 'courier', 'logistics', 'transport', 'bus', 'flight', 'visa', 'rental'], label: 'Travel/Transport', projectKeywords: ['travel', 'tour', 'booking', 'trip', 'transport', 'cab'] },
            { keywords: ['hostel', 'pg', 'paying guest', 'stay', 'accommodation', 'lodge', 'guest house', 'homestay', 'dormitory'], label: 'Hostel/Accommodation', projectKeywords: ['hostel', 'buddy', 'stay', 'accommodation', 'booking', 'room'] },
        ];
        
        // Find the matching category group
        let matchedGroup = null;
        for (const group of categoryKeywordMap) {
            if (group.keywords.some(kw => searchText.includes(kw))) {
                matchedGroup = group;
                break;
            }
        }
        
        if (matchedGroup) {
            // Search portfolio projects for a match using the group's project keywords
            const matchedProject = projects.find(p => {
                const pText = `${p.title} ${p.desc}`.toLowerCase();
                return matchedGroup.projectKeywords.some(kw => pText.includes(kw));
            });
            
            if (matchedProject && matchedProject.demo_url) {
                return `maine haal hi mein ek ${matchedGroup.label} category ka project complete kiya hai, aap is link par live demo dekh sakte hain: ${matchedProject.demo_url}`;
            }
        }
        
        // Fallback: try to find ANY project with a demo URL and describe it generically
        const anyProjectWithDemo = projects.find(p => p.demo_url);
        if (anyProjectWithDemo) {
            return `hamare recent projects mein se ek sample aap yahan dekh sakte hain: ${anyProjectWithDemo.demo_url} — aapke business ke liye bhi similar premium setup bana sakte hain.`;
        }
        
        return `hamare work samples hamare portfolio par dekh sakte hain: ${portfolioUrl}`;
    },
 
    async sendWhatsApp() {
        const lead = AppState.currentWhatsAppLead;
        if (!lead) return;
        
        const btn = document.getElementById('sendWhatsAppBtn');
        const originalText = btn.innerHTML;
        btn.innerHTML = '⏳ Generating...';
        btn.disabled = true;
        
        // Open a blank tab synchronously to prevent popup blockers
        const newWindow = window.open('about:blank', '_blank');
        
        try {
            const previewMessage = document.getElementById('messagePreview')?.textContent || '';
            const data = await API.generateWhatsAppLink(
                lead.whatsapp_number,
                'custom',
                lead,
                previewMessage
            );
            
            if (data.whatsapp_link) {
                let finalLink = data.whatsapp_link;
                
                // Detect mobile vs desktop
                const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
                if (!isMobile) {
                    // Bypass the annoying intermediate page on desktop by routing to web.whatsapp.com directly
                    finalLink = finalLink.replace('api.whatsapp.com/send', 'web.whatsapp.com/send');
                }
                
                if (newWindow) {
                    newWindow.location.href = finalLink;
                } else {
                    // Fallback in case popup blocker still stopped window.open
                    window.open(finalLink, '_blank');
                }
                
                this.closeDetailPane();
                UI.showToast(`WhatsApp opened for ${lead.name}`, 'success');
                
                try {
                    lead.contacted = 1;
                    lead.contact_date = new Date().toISOString();
                    lead.pipeline_stage = 'PITCHED';
                    
                    if (lead.id) {
                        await API.request(`/api/leads/${lead.id}/contact`, {
                            method: 'POST',
                            body: JSON.stringify({ notes: lead.notes || 'Contacted via WhatsApp' })
                        });
                    }
                    
                    UI.renderLeads(AppState.leads);
                    
                    if (lead.id) {
                        setTimeout(() => {
                            this.promptFollowupReminder(lead.id, lead.name);
                        }, 500);
                    }
                } catch (contactErr) {
                    console.error('Error marking contacted:', contactErr);
                }
            } else {
                if (newWindow) newWindow.close();
                UI.showToast('Failed to generate WhatsApp link.', 'error');
            }
        } catch (error) {
            if (newWindow) newWindow.close();
            UI.showToast(error.message, 'error');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    },

    async sendApiWhatsApp() {
        const lead = AppState.currentWhatsAppLead;
        if (!lead) return;

        const body = document.getElementById('messagePreview')?.textContent || '';
        if (!body) {
            UI.showToast('Please generate or type a WhatsApp message first!', 'warning');
            return;
        }

        if (!lead.whatsapp_number) {
            UI.showToast('This lead does not have a WhatsApp number!', 'warning');
            return;
        }

        try {
            UI.showLoading('Dispatching message via WhatsApp API...');
            
            const data = await API.request('/api/outreach/send-whatsapp', {
                method: 'POST',
                body: JSON.stringify({
                    lead_id: lead.id,
                    body: body
                })
            });

            if (data.success) {
                UI.showToast(data.message || 'WhatsApp message successfully sent via API!', 'success');
                this.closeDetailPane();
                
                try {
                    lead.contacted = 1;
                    lead.contact_date = new Date().toISOString();
                    lead.pipeline_stage = 'PITCHED';
                    UI.renderLeads(AppState.leads);
                    
                    if (lead.id) {
                        setTimeout(() => {
                            this.promptFollowupReminder(lead.id, lead.name);
                        }, 500);
                    }
                } catch (contactErr) {
                    console.error('Error marking contacted:', contactErr);
                }
            } else {
                UI.showToast(data.error || 'WhatsApp API dispatch failed.', 'error');
            }
        } catch (error) {
            UI.showToast('WhatsApp API Send failed: ' + error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async generateAIPitch() {
        const lead = AppState.currentWhatsAppLead;
        if (!lead) return;

        const geminiKeyRaw = localStorage.getItem('gemini_api_key');
        const geminiKey = geminiKeyRaw ? await CryptoHelper.decrypt(geminiKeyRaw, AppState.encryptionKey) : '';
        if (!geminiKey) {
            UI.showToast('Please configure your Gemini API Key in Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const projectSample = this.getBestPortfolioProjectSample(lead);
        const tone = UI.el.pitchToneSelect?.value || 'elite';
        const length = UI.el.pitchLengthSelect?.value || 'detailed';
        const minWords = parseInt(UI.el.pitchMinWordsSelect?.value) || 150;
        let service = UI.el.pitchServiceSelect?.value || 'web_design';
        if (service === 'custom') {
            service = UI.el.pitchCustomServiceInput?.value.trim() || 'Custom Service';
        }

        try {
            UI.showLoading('AI Writer generating pitch...');
            
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
                    service: service,
                    min_words: minWords,
                    language: UI.el.pitchLanguageSelect?.value || 'hinglish',
                    sender: {
                        name: localStorage.getItem('sender_name') || '',
                        brand: localStorage.getItem('sender_brand') || '',
                        role: localStorage.getItem('sender_role') || ''
                    },
                    custom_pitch_rules: localStorage.getItem('custom_pitch_rules') || ''
                })
            });

            if (data.success && data.pitch) {
                const customRadio = document.querySelector('input[name="template"][value="custom"]');
                if (customRadio) {
                    customRadio.checked = true;
                    AppState.selectedTemplate = 'custom';
                    
                    const customArea = document.getElementById('customMessageArea');
                    if (customArea) customArea.style.display = 'block';
                    
                    const container = UI.el.templateOptions;
                    if (container) {
                        container.querySelectorAll('.template-option').forEach(o => o.classList.remove('selected'));
                        customRadio.closest('.template-option')?.classList.add('selected');
                    }
                }

                const customMessageInput = document.getElementById('customMessageInput');
                if (customMessageInput) {
                    customMessageInput.value = data.pitch;
                }

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

        const geminiKeyRaw = localStorage.getItem('gemini_api_key');
        const geminiKey = geminiKeyRaw ? await CryptoHelper.decrypt(geminiKeyRaw, AppState.encryptionKey) : '';
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
        const minWords = parseInt(UI.el.pitchMinWordsSelect?.value) || 150;
        let service = UI.el.pitchServiceSelect?.value || 'web_design';
        if (service === 'custom') {
            service = UI.el.pitchCustomServiceInput?.value.trim() || 'Custom Service';
        }

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
                    service: service,
                    min_words: minWords,
                    language: UI.el.pitchLanguageSelect?.value || 'hinglish',
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

    updateSocialMessagePreview() {
        const preview = document.getElementById('socialMessagePreview');
        const customMessageInput = document.getElementById('customSocialMessageInput');
        const customArea = document.getElementById('customSocialMessageArea');
        if (customMessageInput && customMessageInput.value.trim() !== '') {
            if (preview) preview.innerHTML = customMessageInput.value.replace(/\n/g, '<br>');
            if (customArea) customArea.style.display = 'block';
        } else {
            if (preview) preview.innerHTML = 'Click generate to create a custom social media pitch...';
            if (customArea) customArea.style.display = 'none';
        }
    },

    async generateAISocialPitch() {
        const lead = AppState.selectedLead;
        if (!lead) return;

        const geminiKeyRaw = localStorage.getItem('gemini_api_key');
        const geminiKey = geminiKeyRaw ? await CryptoHelper.decrypt(geminiKeyRaw, AppState.encryptionKey) : '';
        if (!geminiKey) {
            UI.showToast('Please configure your Gemini API Key in Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const projectSample = this.getBestPortfolioProjectSample(lead);
        const tone = UI.el.socialToneSelect?.value || 'elite';
        const length = UI.el.socialLengthSelect?.value || 'short';
        const minWords = parseInt(UI.el.socialMinWordsSelect?.value) || 100;
        let service = UI.el.socialServiceSelect?.value || 'social_media';
        if (service === 'custom') {
            service = UI.el.socialCustomServiceInput?.value.trim() || 'Custom Service';
        }

        try {
            UI.showLoading('AI Writer generating social pitch...');
            
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
                    service: service,
                    min_words: minWords,
                    language: UI.el.socialLanguageSelect?.value || 'hinglish',
                    sender: {
                        name: localStorage.getItem('sender_name') || '',
                        brand: localStorage.getItem('sender_brand') || '',
                        role: localStorage.getItem('sender_role') || ''
                    },
                    custom_pitch_rules: localStorage.getItem('custom_pitch_rules') || ''
                })
            });

            if (data.success && data.pitch) {
                const customArea = document.getElementById('customSocialMessageArea');
                if (customArea) customArea.style.display = 'block';

                const customMessageInput = document.getElementById('customSocialMessageInput');
                if (customMessageInput) {
                    customMessageInput.value = data.pitch;
                }

                this.updateSocialMessagePreview();
                UI.showToast('✨ Unique AI Social DM pitch generated successfully!', 'success');
            }
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async refineAISocialPitch() {
        const lead = AppState.selectedLead;
        if (!lead) return;

        const geminiKeyRaw = localStorage.getItem('gemini_api_key');
        const geminiKey = geminiKeyRaw ? await CryptoHelper.decrypt(geminiKeyRaw, AppState.encryptionKey) : '';
        if (!geminiKey) {
            UI.showToast('Please configure your Gemini API Key in Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const customMessageInput = document.getElementById('customSocialMessageInput');
        const previousPitch = customMessageInput?.value.trim() || '';
        const refineFeedback = document.getElementById('socialPitchRefineInput')?.value.trim() || '';

        if (!refineFeedback) {
            UI.showToast('Please enter some refinement feedback first!', 'warning');
            return;
        }

        const projectSample = this.getBestPortfolioProjectSample(lead);
        const tone = UI.el.socialToneSelect?.value || 'elite';
        const length = UI.el.socialLengthSelect?.value || 'short';
        const minWords = parseInt(UI.el.socialMinWordsSelect?.value) || 100;
        let service = UI.el.socialServiceSelect?.value || 'social_media';
        if (service === 'custom') {
            service = UI.el.socialCustomServiceInput?.value.trim() || 'Custom Service';
        }

        try {
            UI.showLoading('AI Writer refining social pitch...');
            
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
                    service: service,
                    min_words: minWords,
                    language: UI.el.socialLanguageSelect?.value || 'hinglish',
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
                
                const refineInput = document.getElementById('socialPitchRefineInput');
                if (refineInput) {
                    refineInput.value = '';
                }

                this.updateSocialMessagePreview();
                UI.showToast('Social pitch refined successfully!', 'success');
            } else {
                UI.showToast(data.error || 'Failed to refine social pitch.', 'error');
            }
        } catch (error) {
            UI.showToast(error.message, 'error');
        } finally {
            UI.hideLoading();
        }
    },

    async openSocialDM(channel) {
        const lead = AppState.selectedLead;
        if (!lead) return;

        const targetUrl = channel === 'instagram' ? lead.instagram : lead.facebook;
        if (!targetUrl) {
            UI.showToast(`No ${channel === 'instagram' ? 'Instagram' : 'Facebook'} profile link available for this lead.`, 'error');
            return;
        }

        const customMessageInput = document.getElementById('customSocialMessageInput');
        const pitchText = customMessageInput?.value.trim() || '';

        if (!pitchText) {
            UI.showToast('Please generate or write a pitch message first!', 'warning');
            return;
        }

        try {
            await navigator.clipboard.writeText(pitchText);
            UI.showToast(`📋 Pitch copied! Opening ${channel === 'instagram' ? 'Instagram' : 'Facebook'}...`, 'success');
        } catch (clipErr) {
            const textArea = document.createElement('textarea');
            textArea.value = pitchText;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            UI.showToast(`📋 Pitch copied! Opening ${channel === 'instagram' ? 'Instagram' : 'Facebook'}...`, 'success');
        }

        setTimeout(() => {
            const sanitizedUrl = UI.sanitizeUrl(targetUrl);
            if (sanitizedUrl !== '#') {
                window.open(sanitizedUrl, '_blank');
            }
        }, 800);
    },

    openEmail(indexOrLead) {
        const lead = typeof indexOrLead === 'object' ? indexOrLead : AppState.leads[indexOrLead];
        if (!lead) return;

        const index = typeof indexOrLead === 'number' ? indexOrLead : AppState.leads.findIndex(l => l.id === lead.id);
        AppState.currentEmailIndex = index;
        AppState.currentEmailLead = lead;

        this.selectLead(lead.id);
        this.switchDetailTab('email');

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
            // Always hide custom service container since we force web_design/seo
            if (UI.el.emailCustomServiceContainer) UI.el.emailCustomServiceContainer.style.display = 'none';
        }
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

    async scanEmailOnDemand() {
        const lead = AppState.currentEmailLead;
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
                const safeIndex = AppState.leads.findIndex(l => l.id === lead.id);
                if (safeIndex !== -1) {
                    AppState.leads[safeIndex].email = data.email;
                }
                
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

        const geminiKeyRaw = localStorage.getItem('gemini_api_key');
        const geminiKey = geminiKeyRaw ? await CryptoHelper.decrypt(geminiKeyRaw, AppState.encryptionKey) : '';
        if (!geminiKey) {
            UI.showToast('Please configure your Gemini API Key in Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const projectSample = this.getBestPortfolioProjectSample(lead);
        const tone = UI.el.emailToneSelect?.value || 'elite';
        const minWords = parseInt(UI.el.emailMinWordsSelect?.value) || 150;
        let service = UI.el.emailServiceSelect?.value || 'web_design';
        if (service === 'custom') {
            service = UI.el.emailCustomServiceInput?.value.trim() || 'Custom Service';
        }

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
                    service: service,
                    min_words: minWords,
                    language: UI.el.emailLanguageSelect?.value || 'hinglish',
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

        this.closeDetailPane();
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
        const passwordRaw = localStorage.getItem('smtp_password') || '';
        const password = passwordRaw ? await CryptoHelper.decrypt(passwordRaw, AppState.encryptionKey) : '';
        const useSSL = localStorage.getItem('smtp_use_ssl') !== 'false';

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
                this.closeDetailPane();
                
                this.markLeadPitched(lead);
            } else {
                UI.showToast(data.error || 'Direct dispatch failed.', 'error');
            }
        } catch (error) {
            if (error.message && (error.message.includes('BadCredentials') || error.message.includes('Username and Password not accepted'))) {
                UI.showToast('❌ SMTP Authentication Failed! Google requires an App Password (16-char code from Google Account Security), not your regular Gmail password.', 'error');
            } else if (error.message && (error.message.includes('Limit Exceeded') || error.message.includes('limit exceeded') || error.message.includes('5.4.5'))) {
                UI.showToast('❌ SMTP Daily Sending Limit Exceeded! Google restricts free accounts. Configure a dedicated provider (Brevo, Resend, SendGrid) in Settings, or wait 24 hours.', 'error');
            } else {
                UI.showToast('SMTP Direct Send failed: ' + error.message, 'error');
            }
        } finally {
            UI.hideLoading();
        }
    },

    async sendOmnichannelEmail() {
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
        if (!lead.whatsapp_number) {
            UI.showToast('This lead does not have a WhatsApp number! Use regular Direct Send instead.', 'warning');
            return;
        }
        if (lead.line_type === 'LANDLINE') {
            UI.showToast('This lead has a landline number! WhatsApp cannot be sent. Use regular Direct Send instead.', 'warning');
            return;
        }

        const host = localStorage.getItem('smtp_host') || '';
        const port = localStorage.getItem('smtp_port') || '';
        const email = localStorage.getItem('smtp_email') || '';
        const passwordRaw = localStorage.getItem('smtp_password') || '';
        const password = passwordRaw ? await CryptoHelper.decrypt(passwordRaw, AppState.encryptionKey) : '';
        const useSSL = localStorage.getItem('smtp_use_ssl') !== 'false';

        if (!host || !port || !email || !password) {
            UI.showToast('SMTP is disabled. Configure your SMTP Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        try {
            UI.showLoading('Connecting to SMTP & Meta APIs and dispatching messages...');
            
            const data = await API.request('/api/outreach/send-omnichannel', {
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
                UI.showToast(data.message || 'Omnichannel message successfully sent!', 'success');
                this.closeDetailPane();
                
                this.markLeadPitched(lead);
            } else {
                UI.showToast(data.error || 'Omnichannel dispatch failed.', 'error');
            }
        } catch (error) {
            UI.showToast('Omnichannel Send failed: ' + error.message, 'error');
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
            
            setTimeout(() => {
                this.promptFollowupReminder(lead.id, lead.name);
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
        
        document.querySelectorAll('.reminder-preset-btn').forEach(btn => {
            btn.classList.remove('selected');
            btn.style.borderColor = '';
            btn.style.color = '';
            btn.style.background = '';
            
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
            
            let whatsappBtn = '';
            if (lead.whatsapp_number) {
                whatsappBtn = `<button class="row-btn whatsapp" data-tooltip="WhatsApp Pitch" onclick="App.triggerWhatsAppReminder(${lead.id})" style="padding: 6px; border-radius: 4px;"><svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 20.25c4.97 0 9-3.694 9-8.25s-4.03-8.25-9-8.25S3 7.444 3 12c0 2.104.859 4.023 2.273 5.48L4.25 21l3.59-.87A8.966 8.966 0 0 0 12 20.25Z" /></svg></button>`;
            }
            
            let emailBtn = '';
            if (lead.email) {
                emailBtn = `<button class="row-btn email" data-tooltip="Email Pitch" onclick="App.triggerEmailReminder(${lead.id})" style="padding: 6px; border-radius: 4px;"><svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" /></svg></button>`;
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
                        <button class="row-btn delete" data-tooltip="Dismiss Reminder" onclick="App.dismissLeadReminder(${lead.id})" style="border-color: var(--accent-green); color: var(--accent-green); background: rgba(16, 185, 129, 0.05); padding: 6px; border-radius: 4px;"><svg class="icon" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg></button>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    },

    triggerWhatsAppReminder(leadId) {
        const lead = (AppState.reminders || []).find(r => r.id === leadId);
        if (!lead) return;
        
        if (!AppState.leads.find(l => l.id === leadId)) {
            AppState.leads.push(lead);
        }
        
        UI.closeModal('followupsModal');
        setTimeout(() => {
            this.openWhatsApp(lead);
        }, 300);
    },

    triggerEmailReminder(leadId) {
        const lead = (AppState.reminders || []).find(r => r.id === leadId);
        if (!lead) return;
        
        if (!AppState.leads.find(l => l.id === leadId)) {
            AppState.leads.push(lead);
        }
        
        UI.closeModal('followupsModal');
        setTimeout(() => {
            this.openEmail(lead);
        }, 300);
    },

    openEmailCampaign() {
        const campaignLeads = AppState.leads || [];
        
        if (campaignLeads.length === 0) {
            UI.showToast('Search results me aisi koi lead nahi hai! Pehle search run karein.', 'warning');
            return;
        }

        // Preserve existing campaign state if leads haven't changed
        const existingIds = new Set((AppState.campaignLeads || []).map(l => l.id));
        const currentIds = new Set(campaignLeads.map(l => l.id));
        const leadsChanged = campaignLeads.length !== existingIds.size || campaignLeads.some(l => !existingIds.has(l.id));

        if (leadsChanged || !AppState.campaignLeads || AppState.campaignLeads.length === 0) {
            // Build new campaign state, but merge with any existing drafts
            const existingMap = {};
            (AppState.campaignLeads || []).forEach(l => { existingMap[l.id] = l; });

            AppState.campaignLeads = campaignLeads.map(lead => {
                const existing = existingMap[lead.id];
                if (existing && (existing.campaign_draft_status === 'ready' || existing.campaign_send_status === 'sent')) {
                    // Preserve drafted/sent state
                    return { ...lead, ...existing, name: lead.name, email: lead.email || existing.email };
                }
                return {
                    ...lead,
                    campaign_email_status: lead.email ? 'scraped' : 'missing',
                    campaign_draft_status: lead.custom_pitch ? 'ready' : 'not-drafted',
                    campaign_send_status: 'pending',
                    campaign_subject: lead.email ? this.getDefaultSubject() : '',
                    campaign_body: lead.custom_pitch || ''
                };
            });
        }

        AppState.selectedCampaignLeadId = AppState.selectedCampaignLeadId || null;

        this.renderCampaignList();
        this.updateCampaignStats();
        
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

        const countBadge = document.getElementById('campaignDirectoryCount');
        if (countBadge) countBadge.textContent = `${total} lead${total !== 1 ? 's' : ''}`;
    },

    renderCampaignList() {
        const body = UI.el.campaignTableBody;
        if (!body) return;

        const leads = AppState.campaignLeads || [];
        
        body.innerHTML = leads.map((lead, index) => {
            const activeClass = lead.id === AppState.selectedCampaignLeadId ? 'active' : '';
            const safeName = UI.escapeHtml(lead.name);
            const safeWebsite = lead.website ? UI.escapeHtml(lead.website) : '';
            const priorityClass = `priority-${(lead.priority || 'MEDIUM').toLowerCase()}`;
            const priorityEmoji = { HIGH: '🔴', MEDIUM: '🟡', LOW: '🟢', IGNORE: '⚪' }[lead.priority || 'MEDIUM'] || '';

            let websiteLinkHtml = '';
            if (lead.website) {
                const sanitizedWebsite = UI.sanitizeUrl(lead.website);
                websiteLinkHtml = `<a href="${sanitizedWebsite}" target="_blank" class="campaign-card-link">🌐 Website</a>`;
            } else {
                websiteLinkHtml = `<span class="campaign-card-no-link">❌ No Website</span>`;
            }

            let emailHtml = '';
            if (lead.email) {
                emailHtml = `
                    <div class="campaign-card-email-box">
                        <span style="font-size: 0.72rem;">✉️</span>
                        <span class="campaign-card-email-text" title="${UI.escapeHtml(lead.email)}">${UI.escapeHtml(lead.email)}</span>
                    </div>
                `;
            } else if (lead.campaign_email_status === 'scanning') {
                emailHtml = `
                    <div class="campaign-card-email-box scanning">
                        <span class="pulse-dot"></span>
                        <span style="color: var(--accent-cyan); font-style: italic; font-size: 0.75rem;">Scanning...</span>
                    </div>
                `;
            } else if (lead.campaign_email_status === 'failed') {
                emailHtml = `
                    <div style="display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0;">
                        <div class="campaign-card-email-box failed">
                            <span style="color: var(--accent-red); font-size: 0.72rem;">Scan failed</span>
                        </div>
                        <button class="campaign-table-btn scan" onclick="event.stopPropagation(); App.scanCampaignLeadEmailOnDemand(${lead.id}, ${index})" title="Retry Email Scan">🔄 Retry</button>
                    </div>
                `;
            } else {
                emailHtml = `
                    <div style="display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0;">
                        <div class="campaign-card-email-box missing">
                            <span style="color: var(--text-muted); font-size: 0.72rem;">No email</span>
                        </div>
                        <button class="campaign-table-btn scan" onclick="event.stopPropagation(); App.scanCampaignLeadEmailOnDemand(${lead.id}, ${index})">🔍 Scan</button>
                    </div>
                `;
            }

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

            let actionBtn = '';
            if (lead.campaign_send_status === 'sent') {
                actionBtn = `<span class="campaign-sent-check">✓ Sent</span>`;
            } else if (lead.campaign_draft_status === 'ready') {
                actionBtn = `<button class="btn btn-whatsapp btn-sm" onclick="event.stopPropagation(); App.selectCampaignLead(${lead.id}); App.sendCampaignLeadSMTPImmediate(${lead.id}, ${index})" style="font-size: 0.7rem; padding: 4px 8px; background: var(--gradient-primary); color: white; border: none; cursor: pointer; border-radius: 4px; font-weight: 600;">🚀 Send</button>`;
            } else if (lead.email) {
                actionBtn = `<button class="campaign-table-btn draft" onclick="event.stopPropagation(); App.selectCampaignLead(${lead.id}); App.generateCampaignLeadAIDraftImmediate(${lead.id}, ${index})">✨ Draft AI</button>`;
            } else {
                actionBtn = `<span style="color: var(--text-muted); font-size: 0.75rem;">Need Email</span>`;
            }

            return `
                <div id="campaign-row-${lead.id}" class="campaign-lead-card ${activeClass}" onclick="App.selectCampaignLead(${lead.id})">
                    <div class="campaign-card-row">
                        <div class="campaign-card-title" title="${safeName}">${safeName}</div>
                        <span class="priority-badge ${priorityClass}" style="font-size: 0.65rem; padding: 2px 6px; border-radius: 4px;">
                            ${priorityEmoji} ${lead.priority}
                        </span>
                    </div>
                    
                    <div class="campaign-card-row" style="margin-top: 2px;">
                        ${websiteLinkHtml}
                        ${emailHtml}
                    </div>

                    <div class="campaign-card-actions">
                        ${draftBadge}
                        ${actionBtn}
                    </div>
                </div>
            `;
        }).join('');
    },

    selectCampaignLead(leadId) {
        AppState.selectedCampaignLeadId = leadId;
        
        document.querySelectorAll('#campaignTableBody .campaign-lead-card').forEach(card => card.classList.remove('active'));
        const activeRow = document.getElementById(`campaign-row-${leadId}`);
        if (activeRow) activeRow.classList.add('active');

        const lead = (AppState.campaignLeads || []).find(l => l.id === leadId);
        if (!lead) return;

        if (UI.el.campaignOutboxEmptyState) UI.el.campaignOutboxEmptyState.style.display = 'none';
        if (UI.el.campaignOutboxWorkspace) UI.el.campaignOutboxWorkspace.style.display = 'flex';

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

        lead.campaign_subject = UI.el.campaignSubjectInput?.value || '';
        lead.campaign_body = UI.el.campaignBodyInput?.value || '';

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
                lead.campaign_subject = this.getDefaultSubject();
                
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

        const geminiKeyRaw = localStorage.getItem('gemini_api_key');
        const geminiKey = geminiKeyRaw ? await CryptoHelper.decrypt(geminiKeyRaw, AppState.encryptionKey) : '';
        if (!geminiKey) {
            UI.showToast('Gemini API key set karein pehle Settings me!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        try {
            UI.showLoading(`Gemini writing email for ${lead.name}...`);
            const projectSample = this.getBestPortfolioProjectSample(lead);
            const tone = UI.el.campaignToneSelect?.value || UI.el.emailToneSelect?.value || 'elite';
            const minWords = parseInt(UI.el.campaignMinWordsSelect?.value || UI.el.emailMinWordsSelect?.value) || 150;
            let service = UI.el.campaignServiceSelect?.value || UI.el.emailServiceSelect?.value || 'web_design';
            if (service === 'custom') {
                service = UI.el.campaignCustomServiceInput?.value.trim() || UI.el.emailCustomServiceInput?.value.trim() || 'Custom Service';
            }

            const isAutopilot = document.getElementById('campaignAutopilotTargeting')?.checked || false;
            const data = await API.request('/api/outreach/generate-email-ai', {
                method: 'POST',
                headers: { 'X-Gemini-API-Key': geminiKey },
                body: JSON.stringify({
                    lead: lead,
                    project_sample: projectSample,
                    tone: tone,
                    service: service,
                    min_words: minWords,
                    language: UI.el.campaignLanguageSelect?.value || UI.el.emailLanguageSelect?.value || 'hinglish',
                    sender: {
                        name: localStorage.getItem('sender_name') || '',
                        brand: localStorage.getItem('sender_brand') || '',
                        role: localStorage.getItem('sender_role') || ''
                    },
                    custom_pitch_rules: localStorage.getItem('custom_pitch_rules') || '',
                    autopilot: isAutopilot
                })
            });

            if (data.success) {
                lead.campaign_subject = data.subject || this.getDefaultSubject();
                lead.campaign_body = data.body || '';
                lead.campaign_draft_status = 'ready';
                
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
        const passwordRaw = localStorage.getItem('smtp_password');
        const password = passwordRaw ? await CryptoHelper.decrypt(passwordRaw, AppState.encryptionKey) : '';
        const useSSL = localStorage.getItem('smtp_use_ssl') !== 'false';

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
                
                const mainIdx = AppState.leads.findIndex(l => l.id === lead.id);
                if (mainIdx !== -1) {
                    AppState.leads[mainIdx].contacted = 1;
                    AppState.leads[mainIdx].contact_date = new Date().toISOString();
                    AppState.leads[mainIdx].pipeline_stage = 'PITCHED';
                }
                UI.renderLeads(AppState.leads);
                UI.showToast(`Outreach email successfully sent to ${toEmail}!`, 'success');
                
                this.skipCampaignLead();
            } else {
                lead.campaign_send_status = 'failed';
                UI.showToast(data.error || 'SMTP Delivery failed', 'error');
            }
        } catch (error) {
            lead.campaign_send_status = 'failed';
            if (error.message && (error.message.includes('BadCredentials') || error.message.includes('Username and Password not accepted'))) {
                UI.showToast('❌ SMTP Auth Failed! Google requires an App Password, not your regular password. Go to Settings → SMTP.', 'error');
            } else if (error.message && (error.message.includes('Limit Exceeded') || error.message.includes('limit exceeded') || error.message.includes('5.4.5'))) {
                UI.showToast('❌ SMTP Daily Sending Limit Exceeded! Google restricts free accounts. Configure a dedicated provider (Brevo, Resend, SendGrid) in Settings, or wait 24 hours.', 'error');
            } else {
                UI.showToast('Outreach failed: ' + error.message, 'error');
            }
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

    async bulkScanCampaignEmails() {
        const leads = AppState.campaignLeads || [];
        const missingLeads = leads.filter(l => !l.email && l.campaign_email_status !== 'scraped' && l.campaign_email_status !== 'scanning');
        
        if (missingLeads.length === 0) {
            UI.showToast('Scraping process complete! Directory me aisi koi lead nahi hai jise email scan ki zaroorat ho.', 'info');
            return;
        }

        const confirmed = await UI.showConfirm(
            "Bulk Email Scan",
            `Kya aap sabhi ${missingLeads.length} leads ke websites se email automatic deep extract karna chahte hain?\n\nIs process mein website crawling ke sath fallback web searches run honge, jisse aapke SerpApi search credits consume ho sakte hain.`,
            "🔍"
        );
        if (!confirmed) {
            return;
        }

        const container = UI.el.campaignProgressContainer;
        const label = UI.el.campaignProgressLabel;
        const bar = UI.el.campaignProgressBar;
        const percentage = UI.el.campaignProgressPercentage;

        if (container) container.style.display = 'block';
        if (label) label.textContent = 'Auto-Scanning websites for contact emails...';

        this.toggleCampaignBulkButtons(true);

        let processed = 0;
        const total = missingLeads.length;

        for (const lead of missingLeads) {
            const idx = AppState.campaignLeads.findIndex(l => l.id === lead.id);
            if (idx === -1) continue;

            lead.campaign_email_status = 'scanning';
            this.renderCampaignList();

            try {
                const data = await API.request(`/api/leads/${lead.id}/scan-email`, {
                    method: 'POST'
                });

                if (data.success && data.email) {
                    lead.email = data.email;
                    lead.campaign_email_status = 'scraped';
                    lead.campaign_subject = this.getDefaultSubject();
                    
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
            
            await new Promise(resolve => setTimeout(resolve, 200));
        }

        this.toggleCampaignBulkButtons(false);
        UI.showToast(`Auto-Scan finished! Processed ${total} websites successfully.`, 'success');
        
        setTimeout(() => {
            if (container) container.style.display = 'none';
        }, 3000);
    },

    async bulkDraftCampaignAI() {
        const geminiKeyRaw = localStorage.getItem('gemini_api_key');
        const geminiKey = geminiKeyRaw ? await CryptoHelper.decrypt(geminiKeyRaw, AppState.encryptionKey) : '';
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

        const confirmed = await UI.showConfirm(
            "Bulk AI Drafting",
            `Kya aap Gemini AI ke through sabhi ${eligibleLeads.length} leads ke liye automatically 100% unique personalized pitches write karna chahte hain?`,
            "✨"
        );
        if (!confirmed) {
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

        const tone = UI.el.campaignToneSelect?.value || UI.el.emailToneSelect?.value || 'elite';
        const minWords = parseInt(UI.el.campaignMinWordsSelect?.value || UI.el.emailMinWordsSelect?.value) || 150;
        const language = UI.el.campaignLanguageSelect?.value || UI.el.emailLanguageSelect?.value || 'hinglish';
        let service = UI.el.campaignServiceSelect?.value || UI.el.emailServiceSelect?.value || 'web_design';
        if (service === 'custom') {
            service = UI.el.campaignCustomServiceInput?.value.trim() || UI.el.emailCustomServiceInput?.value.trim() || 'Custom Service';
        }

        let processed = 0;
        let consecutiveFailures = 0;
        const total = eligibleLeads.length;

        for (const lead of eligibleLeads) {
            try {
                const projectSample = this.getBestPortfolioProjectSample(lead);

                const isAutopilot = document.getElementById('campaignAutopilotTargeting')?.checked || false;
                const data = await API.request('/api/outreach/generate-email-ai', {
                    method: 'POST',
                    headers: { 'X-Gemini-API-Key': geminiKey },
                    body: JSON.stringify({
                        lead: lead,
                        project_sample: projectSample,
                        tone: tone,
                        service: service,
                        min_words: minWords,
                        language: language,
                        sender: {
                            name: localStorage.getItem('sender_name') || '',
                            brand: localStorage.getItem('sender_brand') || '',
                            role: localStorage.getItem('sender_role') || ''
                        },
                        custom_pitch_rules: localStorage.getItem('custom_pitch_rules') || '',
                        autopilot: isAutopilot
                    })
                });

                if (data.success) {
                    lead.campaign_subject = data.subject || this.getDefaultSubject();
                    lead.campaign_body = data.body || '';
                    lead.campaign_draft_status = 'ready';
                    consecutiveFailures = 0;
                    
                    if (AppState.selectedCampaignLeadId === lead.id) {
                        this.selectCampaignLead(lead.id);
                    }
                } else {
                    lead.campaign_draft_status = 'failed';
                    consecutiveFailures++;
                }
            } catch (err) {
                lead.campaign_draft_status = 'failed';
                consecutiveFailures++;
                console.error(`AI generating failed for lead ${lead.name}:`, err);
                
                // Abort early if 3 consecutive failures (likely a critical issue like invalid API key)
                if (consecutiveFailures >= 3) {
                    UI.showToast(`AI Drafting aborted: ${err.message}. Please re-save your Gemini API Key in Settings.`, 'error');
                    break;
                }
            }

            processed++;
            const pct = Math.round((processed / total) * 100);
            
            if (percentage) percentage.textContent = `${pct}%`;
            if (bar) bar.style.width = `${pct}%`;
            
            this.renderCampaignList();
            this.updateCampaignStats();
            
            await new Promise(resolve => setTimeout(resolve, 200));
        }

        const successCount = eligibleLeads.filter(l => l.campaign_draft_status === 'ready').length;
        const failCount = eligibleLeads.filter(l => l.campaign_draft_status === 'failed').length;
        this.toggleCampaignBulkButtons(false);
        UI.showToast(`✨ Auto-Drafting complete! Drafted: ${successCount}${failCount > 0 ? `, Failed: ${failCount}` : ''}.`, failCount > 0 ? 'warning' : 'success');
        
        setTimeout(() => {
            if (container) container.style.display = 'none';
        }, 3000);
    },

    async bulkSendCampaignSMTP() {
        const host = localStorage.getItem('smtp_host');
        const port = localStorage.getItem('smtp_port');
        const email = localStorage.getItem('smtp_email');
        const passwordRaw = localStorage.getItem('smtp_password');
        const password = passwordRaw ? await CryptoHelper.decrypt(passwordRaw, AppState.encryptionKey) : '';
        const useSSL = localStorage.getItem('smtp_use_ssl') !== 'false';

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

        const confirmed = await UI.showConfirm(
            "Mass Dispatch Campaign",
            `🚀 WARNING (Mass Dispatching Campaign!)\n\nKya aap sabhi ${sendableLeads.length} leads ke liye instant SMTP direct cold emails launch karna chahte hain?`,
            "🚀"
        );
        if (!confirmed) {
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
                // If it's a credentials error, break early instead of retrying all
                if (err.message && (err.message.includes('BadCredentials') || err.message.includes('Username and Password not accepted'))) {
                    UI.showToast('❌ SMTP Auth Failed! Google requires an App Password. Fix in Settings → SMTP, then retry.', 'error');
                    for (const remaining of sendableLeads.slice(processed + 1)) {
                        remaining.campaign_send_status = 'failed';
                    }
                    break;
                }
                // If it's a daily sending limit error, show a highlighted warning and break early
                if (err.message && (err.message.includes('Limit Exceeded') || err.message.includes('limit exceeded') || err.message.includes('5.4.5'))) {
                    UI.showToast('❌ SMTP Daily Sending Limit Exceeded! Google has blocked further outgoing messages for the day. Configure a dedicated provider (Brevo, Resend, SendGrid) in Settings → SMTP, or wait 24 hours.', 'error');
                    for (const remaining of sendableLeads.slice(processed + 1)) {
                        remaining.campaign_send_status = 'failed';
                    }
                    break;
                }
            }

            processed++;
            const pct = Math.round((processed / total) * 100);
            
            if (percentage) percentage.textContent = `${pct}%`;
            if (bar) bar.style.width = `${pct}%`;
            
            this.renderCampaignList();
            this.updateCampaignStats();

            await new Promise(resolve => setTimeout(resolve, 1500));
        }

        const successCount = sendableLeads.filter(l => l.campaign_send_status === 'sent').length;
        const failCount = sendableLeads.filter(l => l.campaign_send_status === 'failed').length;
        this.toggleCampaignBulkButtons(false);
        UI.renderLeads(AppState.leads);
        UI.showToast(`Campaign finished! Delivered: ${successCount}${failCount > 0 ? `, Failed: ${failCount}` : ''}.`, failCount > 0 ? 'warning' : 'success');
        
        setTimeout(() => {
            if (container) container.style.display = 'none';
        }, 3000);
    },

    async runAutopilotCampaign() {
        const leads = AppState.campaignLeads || [];
        if (leads.length === 0) {
            UI.showToast('Search results me aisi koi lead nahi hai! Pehle search run karein.', 'warning');
            return;
        }

        const geminiKeyRaw = localStorage.getItem('gemini_api_key');
        const geminiKey = geminiKeyRaw ? await CryptoHelper.decrypt(geminiKeyRaw, AppState.encryptionKey) : '';
        if (!geminiKey) {
            UI.showToast('Please configure your Gemini API Key in Settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const host = localStorage.getItem('smtp_host');
        const port = localStorage.getItem('smtp_port');
        const email = localStorage.getItem('smtp_email');
        const passwordRaw = localStorage.getItem('smtp_password');
        const password = passwordRaw ? await CryptoHelper.decrypt(passwordRaw, AppState.encryptionKey) : '';
        const useSSL = localStorage.getItem('smtp_use_ssl') !== 'false';

        if (!host || !port || !email || !password) {
            UI.showToast('Please configure your SMTP settings first!', 'error');
            UI.openModal('settingsModal');
            return;
        }

        const confirmed = await UI.showConfirm(
            "Autopilot Campaign",
            `🤖 Autopilot Mode (Scan -> Draft -> Send)\n\nKya aap sabhi ${leads.length} leads ke liye automatic campaign run karna chahte hain?\n\nIs process mein system auto-scan, auto-draft (Gemini), aur auto-send (SMTP) sequential loops mein run execute karega.`,
            "🤖"
        );
        if (!confirmed) {
            return;
        }

        const container = UI.el.campaignProgressContainer;
        const label = UI.el.campaignProgressLabel;
        const bar = UI.el.campaignProgressBar;
        const percentage = UI.el.campaignProgressPercentage;

        if (container) container.style.display = 'block';
        this.toggleCampaignBulkButtons(true);

        try {
            // ==================== PHASE 1: SCAN MISSING EMAILS ====================
            const missingLeads = leads.filter(l => !l.email && l.campaign_email_status !== 'scraped');
            if (missingLeads.length > 0) {
                let processedScan = 0;
                for (const lead of missingLeads) {
                    const idx = AppState.campaignLeads.findIndex(l => l.id === lead.id);
                    if (idx === -1) continue;

                    lead.campaign_email_status = 'scanning';
                    this.renderCampaignList();

                    if (label) label.textContent = `🤖 Autopilot Phase 1/3: Scanning website for "${lead.name}" (${processedScan + 1}/${missingLeads.length})...`;

                    try {
                        const data = await API.request(`/api/leads/${lead.id}/scan-email`, {
                            method: 'POST'
                        });

                        if (data.success && data.email) {
                            lead.email = data.email;
                            lead.campaign_email_status = 'scraped';
                            lead.campaign_subject = this.getDefaultSubject();
                            
                            if (AppState.selectedCampaignLeadId === lead.id) {
                                this.selectCampaignLead(lead.id);
                            }
                        } else {
                            lead.campaign_email_status = 'failed';
                        }
                    } catch (err) {
                        lead.campaign_email_status = 'failed';
                    }

                    processedScan++;
                    const pct = Math.round((processedScan / missingLeads.length) * 100);
                    if (percentage) percentage.textContent = `${pct}%`;
                    if (bar) bar.style.width = `${pct}%`;
                    
                    this.renderCampaignList();
                    this.updateCampaignStats();
                    
                    await new Promise(resolve => setTimeout(resolve, 200));
                }
            }

            // ==================== PHASE 2: AUTO-DRAFT AI EMAILS ====================
            const eligibleLeads = leads.filter(l => l.email && l.campaign_draft_status !== 'ready');
            if (eligibleLeads.length > 0) {
                const tone = UI.el.campaignToneSelect?.value || UI.el.emailToneSelect?.value || 'elite';
                const minWords = parseInt(UI.el.campaignMinWordsSelect?.value || UI.el.emailMinWordsSelect?.value) || 150;
                const language = UI.el.campaignLanguageSelect?.value || UI.el.emailLanguageSelect?.value || 'hinglish';
                let service = UI.el.campaignServiceSelect?.value || UI.el.emailServiceSelect?.value || 'web_design';
                if (service === 'custom') {
                    service = UI.el.campaignCustomServiceInput?.value.trim() || UI.el.emailCustomServiceInput?.value.trim() || 'Custom Service';
                }

                let processedDraft = 0;
                if (bar) bar.style.width = '0%';
                if (percentage) percentage.textContent = '0%';

                for (const lead of eligibleLeads) {
                    const idx = AppState.campaignLeads.findIndex(l => l.id === lead.id);
                    if (idx === -1) continue;

                    if (label) label.textContent = `🤖 Autopilot Phase 2/3: Drafting AI pitch for "${lead.name}" (${processedDraft + 1}/${eligibleLeads.length})...`;

                    try {
                        const projectSample = this.getBestPortfolioProjectSample(lead);

                        const isAutopilot = document.getElementById('campaignAutopilotTargeting')?.checked || false;
                        const data = await API.request('/api/outreach/generate-email-ai', {
                            method: 'POST',
                            headers: { 'X-Gemini-API-Key': geminiKey },
                            body: JSON.stringify({
                                lead: lead,
                                project_sample: projectSample,
                                tone: tone,
                                service: service,
                                min_words: minWords,
                                language: language,
                                sender: {
                                    name: localStorage.getItem('sender_name') || '',
                                    brand: localStorage.getItem('sender_brand') || '',
                                    role: localStorage.getItem('sender_role') || ''
                                },
                                custom_pitch_rules: localStorage.getItem('custom_pitch_rules') || '',
                                autopilot: isAutopilot
                            })
                        });

                        if (data.success) {
                            lead.campaign_subject = data.subject || this.getDefaultSubject();
                            lead.campaign_body = data.body || '';
                            lead.campaign_draft_status = 'ready';
                            
                            if (AppState.selectedCampaignLeadId === lead.id) {
                                this.selectCampaignLead(lead.id);
                            }
                        }
                    } catch (err) {
                        console.error(`AI generation failed for lead ${lead.name}:`, err);
                    }

                    processedDraft++;
                    const pct = Math.round((processedDraft / eligibleLeads.length) * 100);
                    if (percentage) percentage.textContent = `${pct}%`;
                    if (bar) bar.style.width = `${pct}%`;
                    
                    this.renderCampaignList();
                    this.updateCampaignStats();
                    
                    await new Promise(resolve => setTimeout(resolve, 200));
                }
            }

            // ==================== PHASE 3: BULK SMTP DISPATCH ====================
            const sendableLeads = leads.filter(l => l.campaign_draft_status === 'ready' && l.campaign_send_status !== 'sent');
            let successfullySent = 0;
            let lastSendError = '';
            if (sendableLeads.length > 0) {
                let processedSend = 0;
                if (bar) bar.style.width = '0%';
                if (percentage) percentage.textContent = '0%';

                for (const lead of sendableLeads) {
                    const idx = AppState.campaignLeads.findIndex(l => l.id === lead.id);
                    if (idx === -1) continue;

                    lead.campaign_send_status = 'sending';
                    this.renderCampaignList();

                    if (label) label.textContent = `🤖 Autopilot Phase 3/3: Dispatching email to "${lead.email}" (${processedSend + 1}/${sendableLeads.length})...`;

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
                            successfullySent++;
                            
                            const mainIdx = AppState.leads.findIndex(l => l.id === lead.id);
                            if (mainIdx !== -1) {
                                AppState.leads[mainIdx].contacted = 1;
                                AppState.leads[mainIdx].contact_date = new Date().toISOString();
                                AppState.leads[mainIdx].pipeline_stage = 'PITCHED';
                            }
                        } else {
                            lead.campaign_send_status = 'failed';
                            lastSendError = data.error || 'Unknown send error';
                        }
                    } catch (err) {
                        lead.campaign_send_status = 'failed';
                        lastSendError = err.message || 'Send failed';
                        // If it's a credentials error, show immediately and stop wasting time
                        if (err.message && (err.message.includes('BadCredentials') || err.message.includes('Username and Password not accepted'))) {
                            UI.showToast('❌ SMTP Authentication Failed! Google requires an App Password, not your regular password. Go to Settings → SMTP to fix.', 'error');
                            // Mark all remaining as failed
                            for (const remaining of sendableLeads.slice(processedSend + 1)) {
                                remaining.campaign_send_status = 'failed';
                            }
                            break;
                        }
                        // If it's a daily sending limit error, show a highlighted warning and break early
                        if (err.message && (err.message.includes('Limit Exceeded') || err.message.includes('limit exceeded') || err.message.includes('5.4.5'))) {
                            UI.showToast('❌ SMTP Daily Sending Limit Exceeded! Google has blocked further outgoing messages for the day. Configure a dedicated provider (Brevo, Resend, SendGrid) in Settings → SMTP, or wait 24 hours.', 'error');
                            for (const remaining of sendableLeads.slice(processedSend + 1)) {
                                remaining.campaign_send_status = 'failed';
                            }
                            break;
                        }
                    }

                    processedSend++;
                    const pct = Math.round((processedSend / sendableLeads.length) * 100);
                    if (percentage) percentage.textContent = `${pct}%`;
                    if (bar) bar.style.width = `${pct}%`;
                    
                    this.renderCampaignList();
                    this.updateCampaignStats();

                    await new Promise(resolve => setTimeout(resolve, 1500));
                }
            }

            UI.renderLeads(AppState.leads);
            const failedSend = sendableLeads.filter(l => l.campaign_send_status === 'failed').length;
            if (successfullySent > 0) {
                UI.showToast(`🤖 Autopilot Campaign finished! Successfully sent: ${successfullySent} cold emails.${failedSend > 0 ? ` (${failedSend} failed)` : ''}`, failedSend > 0 ? 'warning' : 'success');
            } else if (sendableLeads.length > 0) {
                UI.showToast(`❌ Autopilot Campaign: All ${sendableLeads.length} sends failed! ${lastSendError.includes('BadCredentials') ? 'Use a Google App Password instead of your regular password.' : lastSendError}`, 'error');
            } else if (leads.filter(l => l.email).length === 0) {
                UI.showToast('🤖 Autopilot: No emails found for any leads. Email scanning did not return results.', 'warning');
            } else {
                UI.showToast(`🤖 Autopilot Campaign finished! No emails to send (drafts may not be ready).`, 'warning');
            }
        } catch (globalErr) {
            UI.showToast(`Autopilot failed: ${globalErr.message}`, 'error');
        } finally {
            this.toggleCampaignBulkButtons(false);
            setTimeout(() => {
                if (container) container.style.display = 'none';
            }, 3000);
        }
    },

    toggleCampaignBulkButtons(disabled) {
        if (UI.el.campaignBulkScanBtn) UI.el.campaignBulkScanBtn.disabled = disabled;
        if (UI.el.campaignBulkDraftBtn) UI.el.campaignBulkDraftBtn.disabled = disabled;
        if (UI.el.campaignBulkSendBtn) UI.el.campaignBulkSendBtn.disabled = disabled;
        if (UI.el.campaignAutopilotBtn) UI.el.campaignAutopilotBtn.disabled = disabled;
        if (UI.el.campaignSelectedSendBtn) UI.el.campaignSelectedSendBtn.disabled = disabled;
        if (UI.el.campaignSelectedAIGenBtn) UI.el.campaignSelectedAIGenBtn.disabled = disabled;
        
        const btns = [UI.el.campaignBulkScanBtn, UI.el.campaignBulkDraftBtn, UI.el.campaignBulkSendBtn, UI.el.campaignAutopilotBtn];
        btns.forEach(btn => {
            if (btn) btn.style.opacity = disabled ? '0.5' : '1';
        });
    },

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
                    <input type="radio" name="template" value="${UI.escapeHtml(key)}" ${i === 0 ? 'checked' : ''}>
                    <div>
                        <div class="template-name">${UI.escapeHtml(template.name)}</div>
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

    async fetchRecentDelivered() {
        const listContainer = document.getElementById('deliveredMailsList');
        if (!listContainer) return;
        
        try {
            const data = await API.request('/api/outreach/recent-delivered');
            if (data.success && data.logs) {
                const logs = data.logs;
                AppState.recentDeliveredLogs = logs;
                
                if (logs.length === 0) {
                    listContainer.innerHTML = `
                        <div class="empty-state" style="padding: 24px; text-align: center; color: var(--text-secondary);">
                            No emails sent in the last 12 hours.
                        </div>
                    `;
                    return;
                }
                
                listContainer.innerHTML = logs.map(log => {
                    let pillsHtml = '';
                    if (log.clicked) {
                        pillsHtml += `<span class="campaign-status-badge delivered" style="background: rgba(0, 240, 255, 0.1); color: var(--accent-cyan); border: 1px solid rgba(0, 240, 255, 0.2); margin-right: 4px;">Clicked 🎯</span>`;
                    }
                    if (log.opened) {
                        pillsHtml += `<span class="campaign-status-badge draft-ready" style="margin-right: 4px;">Opened 👀</span>`;
                    }
                    pillsHtml += `<span class="campaign-status-badge delivered">Delivered ✅</span>`;
                    
                    const timeStr = new Date(log.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    const safeName = UI.escapeHtml(log.lead_name);
                    const safeEmail = UI.escapeHtml(log.lead_email || '');
                    const templateName = log.template_used ? UI.escapeHtml(log.template_used) : 'N/A';
                    
                    return `
                        <div class="delivered-mail-item" style="background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 12px 16px; display: flex; justify-content: space-between; align-items: center; gap: 12px; transition: all var(--transition-fast);">
                            <div>
                                <div style="font-weight: 700; font-size: 0.95rem; color: var(--text-primary);">${safeName}</div>
                                <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 2px; font-family: monospace;">
                                    ${safeEmail}
                                </div>
                                <div style="margin-top: 6px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                    ${pillsHtml}
                                    <span style="font-size: 0.7rem; color: var(--text-muted); font-family: monospace;">Template: ${templateName}</span>
                                    <span style="font-size: 0.7rem; color: var(--text-muted);">(${timeStr})</span>
                                </div>
                            </div>
                            <div>
                                <button class="btn btn-secondary btn-sm" onclick="App.viewSentEmail(${log.id})" style="font-size: 0.75rem; padding: 6px 12px; border-color: var(--accent-cyan); color: var(--accent-cyan); background: rgba(0, 240, 255, 0.05); cursor: pointer;">👁️ View Message</button>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                listContainer.innerHTML = `
                    <div style="padding: 24px; text-align: center; color: var(--accent-red);">
                        Failed to load recent logs: ${data.error || 'Unknown error'}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error in fetchRecentDelivered:', error);
            listContainer.innerHTML = `
                <div style="padding: 24px; text-align: center; color: var(--accent-red);">
                    Error: ${error.message}
                </div>
            `;
        }
    },

    viewSentEmail(logId) {
        const log = (AppState.recentDeliveredLogs || []).find(l => l.id === logId);
        if (!log) {
            UI.showToast('Email content log not found', 'error');
            return;
        }
        
        const nameText = document.getElementById('sentEmailLeadNameText');
        const toText = document.getElementById('sentEmailToText');
        const templateText = document.getElementById('sentEmailTemplateText');
        const timeText = document.getElementById('sentEmailTimeText');
        const subjectText = document.getElementById('sentEmailSubjectText');
        const iframe = document.getElementById('sentEmailIFrame');
        
        if (nameText) nameText.textContent = log.lead_name || 'Unknown';
        if (toText) toText.textContent = log.lead_email || 'N/A';
        if (templateText) templateText.textContent = log.template_used || 'default';
        if (timeText) timeText.textContent = new Date(log.sent_at).toLocaleString();
        
        let rawContent = log.message_sent || '';
        let subject = '';
        let htmlBody = '';
        
        if (rawContent.startsWith('SUBJECT:')) {
            const lines = rawContent.split('\n');
            const subLine = lines[0];
            subject = subLine.substring(8).trim();
            htmlBody = lines.slice(1).join('\n');
            if (htmlBody.startsWith('BODY:')) {
                htmlBody = htmlBody.substring(5).trim();
            }
        } else {
            subject = log.template_used || 'Outreach Email';
            htmlBody = rawContent;
        }
        
        if (subjectText) subjectText.textContent = subject;
        if (iframe) {
            iframe.srcdoc = htmlBody;
        }
        
        UI.openModal('sentEmailContentModal');
    },

    openOutreachModal(leadId) {
        const lead = AppState.leads.find(l => l.id === leadId);
        if (lead) {
            this.openEmail(lead);
        } else {
            UI.showToast('Lead not found in current view', 'error');
        }
    },
    
    openWhatsAppModal(leadId) {
        const lead = AppState.leads.find(l => l.id === leadId);
        if (lead) {
            this.openWhatsApp(lead);
        } else {
            UI.showToast('Lead not found in current view', 'error');
        }
    },

    async runSocialTask(leadId, profileUrl) {
        const lead = AppState.leads.find(l => l.id === leadId);
        if (!lead) {
            UI.showToast('Lead not found', 'error');
            return;
        }

        let pitch = lead.custom_pitch || `Hi ${lead.name}, I noticed your website has some speed and SEO issues. We would love to help you fix them. Check out your diagnostic report: ${window.location.origin}/preview/${lead.id}`;
        try {
            await navigator.clipboard.writeText(pitch);
            UI.showToast('📋 Pitch copied to clipboard!', 'success');
        } catch (err) {
            console.error('Clipboard copy failed:', err);
            const ta = document.createElement('textarea');
            ta.value = pitch;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            UI.showToast('📋 Pitch copied to clipboard!', 'success');
        }

        if (profileUrl && profileUrl !== '#') {
            window.open(profileUrl, '_blank');
        } else {
            UI.showToast('Opening social task manual workflow...', 'info');
        }

        try {
            const res = await API.request(`/api/outreach/complete-social-task/${leadId}`, {
                method: 'POST'
            });
            if (res && res.success) {
                UI.showToast('Day 5 Social Task completed successfully!', 'success');
                lead.social_task_status = 'COMPLETED';
                lead.social_task_completed_at = new Date().toISOString();
                UI.renderLeads(AppState.leads);
            } else {
                UI.showToast(res.error || 'Failed to update task status', 'error');
            }
        } catch (err) {
            console.error('Error completing social task:', err);
            UI.showToast('Network error updating task status', 'error');
        }
    }
};
