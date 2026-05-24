# LeadHunter AI - Lead Generation Agent 🎯

Yeh ek advanced **AI Lead Generation Agent** hai jo automatically un local businesses ko dhoondhta hai jinki koi website (online presence) nahi hai. Is tool ka main maksad un businesses ki details nikalna aur unhe website development ya digital marketing ki services offer karne mein madad karna hai.

---

## 🌟 Yeh Agent Kya Kya Kar Sakta Hai? (Features)

1. **Smart Local Search:**
   - Aap kisi bhi business type (jaise: Gym, Cafe, Salon) aur city (jaise: Bhopal, Delhi) ka naam daalkar search kar sakte hain.
   - Agent automatically saari details nikalega: Business Name, Phone Number, Address, Website, Rating, aur Reviews.

2. **Intelligent Lead Filtering & Scoring:**
   - Agent automatically un businesses ko **IGNORE** kar deta hai jinki pehle se website hai (Website evidence column mein dynamic red/green badges dikhte hain).
   - Jinki website nahi hai, unhe unke Google Reviews ke hisaab se **Priority Score** deta hai:
     - 🔴 **HIGH Priority:** Jinke paas website nahi hai aur reviews bhi kam hain (<50). Ye sabse acche clients hain.
     - 🟡 **MEDIUM Priority:** Reviews theek hain (50-200) par website nahi hai.
     - 🟢 **LOW Priority:** Bohot zyada reviews hain (>200) par website nahi hai.

3. **WhatsApp Outreach (Auto-Messaging):**
   - Agent ke paas pehle se bane hue WhatsApp Message templates hain (jaise: Website Pitch).
   - Agent message ko **Personalize** karta hai (message mein automatically business ka naam, uski city, aur reviews daal deta hai).
   - Upgraded WhatsApp API connection click karne par bina kisi popup blocker ke WhatsApp Web ya App open kar deta hai.

4. **Data Cleaning & Management:**
   - Phone numbers ko automatically sahi WhatsApp format (jaise +91...) mein convert karta hai.
   - Duplicate businesses ko automatically hata deta hai taaki aapko clean data mile.
   - Har lead ko apne SQLite Database mein hamesha ke liye save karta hai.

5. **One-Click Excel Export:**
   - Aap poore data ko ek click mein properly formatted **Excel (.xlsx)** file mein download kar sakte hain, jisme columns ki width auto-adjusted hoti hai taaki phone numbers cut ya deform na hon.

6. **Deep Scan (Multi-Zone Search):**
   - Pure shehar ke alag-alag zones/areas ko ek saath scan karne ka dynamic feature. City name enter karne par popular zones (jaise MP Nagar, Kolar in Bhopal) automatically suggest ho jaate hain.

7. **Fresh Leads Filter (No Repeats):**
   - Database se matching leads check karke duplicate results ko filter karta hai, aur automatic page-by-page fetch tab tak karta hai jab tak required count ke barabar bilkul naye aur unseen leads na mil jayein. Same responses repeat nahi hote.

---

## 🔌 Kaun-Kaun si API Use Hui Hai?

Is project mein main data extraction ke liye **SerpApi (Google Maps Engine)** ka use hua hai:

- **SerpApi:** Yeh ek powerful API hai jo bilkul exact Google Maps ka data nikal kar deti hai. 
  - **Fayda:** Isme free tier (100 searches/month) milta hai aur Google Cloud ki tarah credit card verify karne ka koi jhanjhat nahi hai.
- **Python / Flask (Backend):** Backend mein data fetch karne, filter karne, aur serve karne ke liye.
- **SQLite:** Data ko locally save karne ke liye (bin kisi external database API ke).

*(Note: Iska architecture "Extensible" banaya gaya hai. Pehle isme direct Google Places API (New) use hui thi, jise baad mein SerpApi se switch kiya gaya).*

---

## 🚀 Room for Improvement (Future Scope)

Kyunki iska code ek 'BaseCollector' architecture par bana hai, isme aage chal kar kaafi naye aur powerful features add kiye ja sakte hain:

1. **Naye Platforms ka Integration:**
   - **Instagram / Facebook Collector:** Agent Instagram se un local businesses ko nikal sakta hai jo active toh hain, par unke bio mein website ka link nahi hai.
   - **JustDial / Sulekha Collector:** Indian market ke aur zyada deep data ke liye.

2. **AI Message Writer (ChatGPT/Claude Integration):**
   - Abhi messages templates ke zariye ban rahe hain. Aage chal kar hum AI ka use karke har dukan ke reviews padh kar ek bilkul unique message likhwa sakte hain (e.g., *"Maine dekha ki aapki rating 4.8 hai par website na hone se aap customers kho rahe hain..."*).

3. **Automated Follow-ups & Emails:**
   - WhatsApp ke alawa, agar agent ko business ka email mile, toh wo khud ek cold-email draft karke bhej sake.
   - Jin logo ko message bhej diya, unhe 3 din baad ek automated reminder message bhej sake.

4. **Bulk WhatsApp Sender:**
   - Abhi hume ek-ek karke message bhejna padta hai. Future mein WhatsApp Business API ya kisi automation tool (jaise Selenium) se hum poori list ko ek saath message bhej sakte hain.

---
*Created as a powerful, modular tool for local business outreach.*
