import os

file_path = r"static\js\modules\whatsapp_outreach.js"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace cases correctly
content = content.replace("lead.phone || existing.phone", "(lead.phone || lead.whatsapp_number) || existing.phone")
content = content.replace("lead.phone ? 'found' : 'missing'", "(lead.phone || lead.whatsapp_number) ? 'found' : 'missing'")
content = content.replace("l => l.phone || l.whatsapp_phone_status", "l => (l.phone || l.whatsapp_number) || l.whatsapp_phone_status")
content = content.replace("if (lead.phone) {", "const thePhone = lead.phone || lead.whatsapp_number;\n            if (thePhone) {")
content = content.replace("UI.escapeHtml(lead.phone)", "UI.escapeHtml(thePhone)")
content = content.replace("lead.phone || 'No Phone Number'", "(lead.phone || lead.whatsapp_number) || 'No Phone Number'")
content = content.replace("l => l.phone && l.whatsapp_draft_status", "l => (l.phone || l.whatsapp_number) && l.whatsapp_draft_status")
content = content.replace("phone: lead.phone,", "phone: lead.phone || lead.whatsapp_number,")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed phone number references in whatsapp_outreach.js")
