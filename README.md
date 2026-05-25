# LeadHunter AI - Lead Generation Agent 🎯

Yeh ek advanced aur modern **AI Lead Generation Agent** hai jo automatically un local businesses ko dhoondhta hai jinki koi website (online presence) nahi hai. Is tool ka main maksad un businesses ki details nikalna aur unhe website development, SEO, ya digital marketing ki services pitch karke new clients acquire karne mein madad karna hai.

Iska dynamic web dashboard modern UI, high-performance database management, and direct outreach mechanisms ke saath aata hai taaki aapka outreach workflow 10x fast ho sake.

---

## 🌟 Supercharged Features (Agent Kya-Kya Kar Sakta Hai?)

1. **Smart Local Search (Google Maps Powered):**
   - Kisi bhi business type (e.g. Gym, Cafe, Salon, Boutique) aur city (e.g. Bhopal, Delhi, Mumbai) ka naam daalkar highly accurate Google Maps data extract karein.
   - Agent automatically saari key details nikalega: Business Name, Phone Number, Address, Website, Rating, aur Reviews.

2. **Intelligent Lead Filtering & Priority Scoring:**
   - **Ignore Existing Websites:** Jin businesses ki website pehle se active hai, unhe automatically identify karke IGNORE kar diya jata hai.
   - **Smart Scoring Badges:** Baaki bache leads ko unke review volumes ke mutabik outreach priority rank karta hai:
     - 🔴 **HIGH Priority:** No Website + Low Reviews (<50). Yeh clients convert hone ke sabse aasaan aur perfect targets hain.
     - 🟡 **MEDIUM Priority:** No Website + Moderate Reviews (50-200). Achi reputation hai par online presence ki kami hai.
     - 🟢 **LOW Priority:** No Website + High Reviews (>200). Bare businesses jo website build karne ke liye easily budget pay kar sakte hain.

3. **Instagram & Facebook Social Scanner (On-Demand):**
   - SerpApi organic search engine ka use karke ek click mein specific business ke active **Instagram** aur **Facebook** profiles ko Google par scan karein.
   - Precision filters use hote hain taaki tags, reels, posts, ya sharing links ko filter out karke direct profiles hi milein.

4. **Instagram DM Link & Pitch Auto-Copy (100% Safe):**
   - Instagram profiles load hone par outreach risk-free aur continuous ho jata hai!
   - Instagram DM button click karne par personalized outreach pitch automatically aapke system clipboard par copy ho jati hai aur unka profile browser window mein launch ho jata hai.
   - **Safety First:** Zero API bans! Kisi auto-bot APIs ka use nahi kiya gaya hai jo aapke Instagram accounts block kar sakein.

5. **WhatsApp Outreach (Auto-Messaging & Verification):**
   - Sahi country codes (+91 for India) aur formatting automatically adjust karta hai.
   - Built-in dynamic and customized outreach templates jo automatically client name, category, and specific reviews count insert kar dete hain.
   - Upgraded WhatsApp API connection bina popup blockers ke WhatsApp Web ya Desktop App seamless tarike se open karta hai.

6. **Next-Page Pagination (Load More Leads):**
   - Index-offset pagination system built directly in backend endpoints and frontend control state.
   - Aap dynamic "Load More" search features ke zariye target count badha kar page-by-page infinite leads scan kar sakte hain. Saari leads single page par accumulate hoti hain, jisse huge export lists fetch karna smooth ho jata hai.

7. **Smart Database Auto-Cleanup (Startup Optimizer):**
   - Startup par background automatic clean-up routine chalta hai jo database storage optimize rakhta hai:
     - **Logs Protection:** Jin leads ko aapne contact kar liya hai, unhe hamesha secure rakha jata hai.
     - **Old Uncontacted Leads:** 14 din se purane uncontacted leads automatically delete ho jate hain.
     - **Old Ignored Leads:** Jinki website pehle se hai aur wo IGNORE state mein hain, unhe 7 din mein clear karta hai.
     - **Search History:** 30 din se purane search queries aur parameters list flush ho jate hain.

8. **Manual Database Clean-up (Settings Option):**
   - Settings menu dashboard par single-click manual clear system hai jo database se sabhi uncontacted records aur search histories ko instantly delete kar deta hai, keeping only your high-value contacted clients safe.

9. **Deep Scan Multi-Zone Suggestions (10+ Indian Cities):**
   - India ke major sheharo (Delhi, Mumbai, Bengaluru, Pune, Hyderabad, Chennai, Kolkata, Ahmedabad, Jaipur, Bhopal) ke popular high-potential commercial zones and sub-localities auto-suggest ho jati hain.
   - Shehar bhar ke micro-areas ko individually aur detailed scan karne ke liye deep scan support active hai.

10. **One-Click Excel Export (Premium Format):**
    - Sahi formatted `.xlsx` (Excel) download.
    - Columns ki sizes auto-adjusted hoti hain taaki mobile numbers text format mein deform ya cut na ho. Priority status, scores, aur page tracking Excel sheets mein complete data capture karte hain.

11. **Premium Modern Dark UI (Wow Aesthetics):**
    - High-quality visual glassmorphism, responsive components, smooth cyan-to-violet colors gradients, soft card entry animations, aur clean interactive visual feedback features design kiye gaye hain.

12. **Smart Portfolio Scraper & Keyword Matcher (Dynamic Outreach):**
    - Settings mein apna portfolio URL (e.g. `https://raunaksharmaq64.github.io/portfolio/`) save karein. Backend automatically page ko scrape karke saare projects aur unke live demo links extract kar lega.
    - WhatsApp dynamic templates mein naye **`{project_sample}`** variable ke zariye hamara unique matching engine (Gym, Hotel/Restaurant, Hostel/PG) dynamically sabse best-fit project demo link pitch message mein append kar deta hai.

13. **Stateless Browser-Safe Storage (Render/Vercel Ready):**
    - Multi-user safe aur 100% cloud-ready architecture. Users ki SerpApi keys aur portfolio projects server-side database ya `.env` files ke bajaye unke browser ke **`localStorage`** mein secure save rehti hain.
    - Isse server-side par dynamic file writing ki jarurat nahi hoti aur aapki personal search limits/credits bilkul surakshit rehte hain. Yeh system multiple users ke liye bin kisi collision ke perfect chalta hai.

14. **Gemini AI Outreach Personalization Writer (Hinglish Elite Persona):**
    - Settings mein optional **Gemini API Key** (Google AI Studio se bilkul free milne wali) save karein. 
    - WhatsApp modal ke andar **`✨ AI Generate Custom Pitch`** click karne par hamara **17+ years experience digital marketer** persona active ho jata hai jo client ke business details, Google rating/reviews aur aapke matched portfolio project sample link ko read karke ekdam warm, friendly, persuasive sales outreach copy write karta hai.
    - Ye bilkul human-like lagti hai (no generic AI phrasing) aur isse response/conversion rates 10x badh jaate hain!

---

## 🔌 Tech Stack & Integrations

- **Backend:** Python + Flask (Robust API routing, server management, custom utility architectures)
- **Frontend:** Responsive HTML5, Vanilla CSS3 (Glassmorphism design language, transitions & micro-animations), Modern Javascript (Dynamic dashboard DOM handling, async fetch control)
- **Database:** SQLite3 (Highly responsive local data storing with dynamic schema migrations)
- **APIs:**
  - **SerpApi (Google Maps Engine):** Exact local businesses lists search ke liye.
  - **SerpApi (Organic Engine):** On-demand social scanner features ke liye.

---

## 📂 Project Directory Structure

```
ai_agent/
├── app.py                     # Main Flask routing, configuration, and endpoint definitions
├── database.py                # Database controllers, stats calculator, auto & manual cleanups
├── requirements.txt           # Python environment packages specification
├── .env                       # API Configuration parameters (Secret)
├── .env.example               # Template file for secret configurations
├── .gitignore                 # Excluded directories and .env files registry
├── README.md                  # Detailed Hinglish guidelines & overview
│
├── collectors/                # Core Data Extraction logic
│   ├── base_collector.py      # Abstract blueprint base model for future platforms integration
│   └── serpapi_collector.py   # SerpApi engine implementation for Google Maps searches
│
├── utils/                     # Smart text processing utility systems
│   ├── data_cleaner.py        # Duplicate remover, contact info cleaner, and scoring calculator
│   ├── whatsapp.py            # Phone prependers and dynamic templates writer
│   ├── portfolio.py           # Smart HTML portfolio scraper and keyword matcher
│   └── ai_writer.py           # Elite Gemini AI sales pitch generator
│
├── templates/                 # UI View System
│   └── index.html             # High-end desktop user-dashboard template
│
└── static/                    # Dynamic Design and Dashboard controller files
    ├── css/
    │   └── style.css          # Core CSS styling system, glassmorphism layouts, and animations
    └── js/
        └── app.js             # State managers, outreach launchers, dynamic pagination, and API fetches
```

---

## 🚀 Setup & Installation (Hinglish Guide)

Follow steps to set up this premium lead finder tool in your local workspace:

### 1. Repository Clone or Directory Navigation
Sabse pehle project directory ko command line par open karein:
```bash
cd "c:\Users\Sahil\Desktop\ai agents"
```

### 2. Install Python Dependencies
Requirements list me add kiye gaye packages ko install karein (requires Python 3.8+):
```bash
pip install -r requirements.txt
```

### 3. API Key setup in Environment
`env` configuration ke liye workspace mein `.env` file banayein ya `.env.example` ko copy karke save karein. 
Isme apni SerpApi key input karein:
```env
SERPAPI_KEY=your_serpapi_private_key_here
```
*(Note: Aap direct dashboard par run-time me settings button click karke bhi dynamic key update kar sakte hain jo automatically `.env` par persist ho jaati hai).*

### 4. Run the Application
Start the Flask dev server:
```bash
python app.py
```
Iske baad server running message dikhega and you can open:
👉 **[http://localhost:5000](http://localhost:5000)** inside your browser!

### 5. Production Cloud Deployment (Render Guide)
Agar aap is project ko internet par live karke friends ke sath share karna chahte hain, toh **Render** par free mein deploy kar sakte hain:
1. GitHub par ek **Private** repository banakar code push karein.
2. [Render.com](https://render.com) par login karke **"New Web Service"** choose karein aur apni repo connect karein.
3. Configure settings:
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** `Free`
4. *Dhyan dein:* Har user apni khud ki SerpApi Key aur Portfolio settings mein browser local storage ke through save karega. Isse aapki keys aur limits bilkul 100% surakshit rahengi!

---

## 🚀 Room for Upgradation & Improvement (Future Scope)

Is agent ka code highly extensible abstract structures ke saath likha gaya hai. Future updates mein in features ko successfully add kiya ja sakta hai:

1. **AI Message Writer (ChatGPT/Claude API Integration):**
   - Abhi personalizations simple string substitutions use karti hain.
   - Future upgrade me, hum AI use karke client ke top reviews, specific issues, aur locality read kar payenge taaki bilkul unique outreach proposal create kiya ja sake.

2. **Full-Scale Lead Scrapers Extensions:**
   - `BaseCollector` framework ka reuse karke JustDial, Sulekha, YellowPages, aur Yelp ke liye native collectors dynamic bindings direct write ki ja sakti hain.

3. **Automated Continuous Email Cold-Outreach:**
   - Scan profiles me business email identify karke single click dynamic email auto-sender with standard SPF/DKIM verification tools deploy ho sakte hain.

4. **Multi-Channel CRM Pipeline:**
   - Leads list ko "Contacted", "Interested", "Converted", "No-Response" boards me visualize karne ke liye dynamic Kanban system view dashboard add karna.

5. **Outreach Scheduler & Analytics:**
   - Leads ko target scheduling intervals par auto WhatsApp Web messages automate karne ke liye integration mechanisms with background processes (like Celery/Redis).

---
*Developed with love for high-speed local business outreach and digital growth.* 🎯
