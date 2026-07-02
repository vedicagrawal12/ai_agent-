import re

with open('static/js/modules/ui.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if "emailCampaignModal:" in line:
        start_idx = i
    if "campaignEmailVisualPreview:" in line:
        end_idx = i

if start_idx != -1 and end_idx != -1:
    email_modal_lines = lines[start_idx:end_idx+1]
    
    whatsapp_lines = []
    whatsapp_lines.append("\n            // WhatsApp Campaign modal elements\n")
    for line in email_modal_lines:
        new_line = line.replace('emailCampaignModal', 'whatsappCampaignModal')
        new_line = new_line.replace('campaign', 'whatsappCampaign')
        new_line = new_line.replace('previewBusinessName', 'whatsappPreviewBusinessName')
        new_line = new_line.replace('previewDeveloperBrand', 'whatsappPreviewDeveloperBrand')
        whatsapp_lines.append(new_line)
    
    new_file_lines = lines[:end_idx+1] + whatsapp_lines + lines[end_idx+1:]
    
    with open('static/js/modules/ui.js', 'w', encoding='utf-8') as f:
        f.writelines(new_file_lines)
    print('Successfully generated and injected WhatsApp UI properties')
else:
    print('Could not find boundaries')
