/**
 * LeadHunter AI — State Management Module
 */

export const AppState = {
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
