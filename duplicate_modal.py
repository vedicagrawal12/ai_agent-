import os

with open('templates/partials/modals.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

email_modal_lines = lines[271:470]
email_modal_text = ''.join(email_modal_lines)

# Replace identifiers and texts
whatsapp_modal_text = email_modal_text.replace('Email Campaign Modal', 'WhatsApp Campaign Modal')
whatsapp_modal_text = whatsapp_modal_text.replace('emailCampaignModal', 'whatsappCampaignModal')
whatsapp_modal_text = whatsapp_modal_text.replace('Cold Email Campaign Center', 'WhatsApp Campaign Center')
whatsapp_modal_text = whatsapp_modal_text.replace('id="campaign', 'id="whatsappCampaign')
whatsapp_modal_text = whatsapp_modal_text.replace('for="campaign', 'for="whatsappCampaign')
whatsapp_modal_text = whatsapp_modal_text.replace('Emails Scraped:', 'Phones Found:')
whatsapp_modal_text = whatsapp_modal_text.replace('Scan All Emails', 'Scan All Phones')
whatsapp_modal_text = whatsapp_modal_text.replace('Send All Drafts (SMTP)', 'Send All Drafts (Meta API)')
whatsapp_modal_text = whatsapp_modal_text.replace('Send SMTP', 'Send Meta API')
whatsapp_modal_text = whatsapp_modal_text.replace('Email Message Body', 'WhatsApp Message Body')
whatsapp_modal_text = whatsapp_modal_text.replace('Email subject line...', 'WhatsApp not required...')
whatsapp_modal_text = whatsapp_modal_text.replace('Draft AI Email', 'Draft AI WhatsApp')
whatsapp_modal_text = whatsapp_modal_text.replace('campaignEmailVisualPreview', 'whatsappCampaignVisualPreview')

# Insert back at line 471
new_lines = lines[:471] + [whatsapp_modal_text + '\n'] + lines[471:]

with open('templates/partials/modals.html', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print('Successfully generated and injected WhatsApp modal')
