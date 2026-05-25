# LeadHunter AI - Lead Generation Agent 🎯

**LeadHunter AI** ek advanced aur modern **AI Lead Generation Agent** hai jo automatically un local businesses ko dhoondhta hai jinki koi website (online presence) nahi hai ya jinse listed website **broken/down** ho gayi hai. Is tool ka main maksad un businesses ki details nikalna, unki contact line classify karna aur unhe website development, SEO, ya digital marketing ki services pitch karke new clients acquire karne mein madad karna hai.

Iska dynamic web dashboard premium modern aesthetics (glassmorphism), high-performance database management, direct outreach mechanisms, aur parallel automation systems ke saath aata hai taaki aapka sales pipeline 10x fast ho sake.

---

## 🌟 Supercharged Features (Agent Kya-Kya Kar Sakta Hai?)

1. **Smart Local Search (Google Maps Powered):**
   - Kisi bhi business type (e.g. Gym, Cafe, Salon, Boutique) aur city (e.g. Bhopal, Delhi, Mumbai) ka naam daalkar highly accurate Google Maps data extract karein.
   - Agent automatically saari key details nikalega: Business Name, Phone Number, Address, Website, Rating, aur Reviews.

2. **Parallel Website Health Checker (BUG-4 Robustness):**
   - Implemented a lightweight parallel status checker using `concurrent.futures.ThreadPoolExecutor`.
   - **Broken Site Detection:** Har lead ke website status ko parallel check karta hai (HEAD request fallback to GET). Agar website open nahi hoti (404, 500, ya net error), toh use **🔴 HIGH Priority (⚠️ Broken Site)** badge de diya jata hai.
   - **Timeout Protection:** Strict 3s per-request limits lagayi gayi hain bina kisi global timeout abort risk ke, jisse checking bulletproof aur false-positive free ho jati hai.

3. **High-Accuracy Phone Validator Engine (Google Libphonenumber):**
   - Regex processing ko replace karke industry-grade **Google `phonenumbers` library** integrate ki gayi hai.
   - **Line Classification:** Numbers ko standardize (+91 for India) karke unhe `MOBILE`, `LANDLINE`, ya `UNKNOWN` mein classify karta hai.
   - **WhatsApp Prevention:** Agar business number Landline hai, toh WhatsApp buttons ko dynamically gray-out aur disable kar deta hai with a custom tooltip: *"Landline Number (No WhatsApp)"*, jisse manual outreach effort aur clicks bilkul waste nahi hote!

4. **Intelligent Lead Filtering & Priority Scoring:**
   - **Ignore Active Websites:** Jin businesses ki website sahi chal rahi hai, unhe automatically IGNORE kar diya jata hai.
   - **Broken Websites Bumping:** Jin businesses ki listed website broken hai, unhe goldmine samajh kar instantly **HIGH** priority score ranking de di jati hai!
   - **Smart Scoring Badges:**
     - 🔴 **HIGH Priority:** No Website (or Broken Website!) + Low Reviews (<50). Perfect target clients.
     - 🟡 **MEDIUM Priority:** No Website + Moderate Reviews (50-200). Achi local brand par digital presence absent.
     - 🟢 **LOW Priority:** No Website + High Reviews (>200). Bare brands with massive customer volumes.

5. **XSS Sanitization & Security Guards (BUG-8 Protection):**
   - High-grade front-end HTML escaping utility integrate ki gayi hai jo `&`, `<`, `>`, `"`, aur `'` ko fully sanitize karti hai.
   - Tooltips, business addresses, aur details securely render hoti hain bina kisi attribute breakout ya DOM XSS threat ke.

6. **Instagram & Facebook Social Scanner (On-Demand):**
   - SerpApi organic search engine ka use karke ek click mein specific business ke active **Instagram** aur **Facebook** profiles ko Google par scan karein.
   - Precision filters use hote hain taaki tags, reels, posts, ya sharing links ko filter out karke direct profiles hi milein.

7. **Instagram DM Link & Pitch Auto-Copy (100% Safe):**
   - Instagram DM button click karne par personalized outreach pitch automatically aapke system clipboard par copy ho jati hai aur unka profile browser window mein launch ho jata hai.
   - **Safety First:** Zero API bans! Kisi auto-bot APIs ka use nahi kiya gaya hai jo aapke Instagram accounts block kar sakein.

8. **Next-Page Pagination (Load More Leads):**
   - Index-offset pagination system ke zariye dynamic "Load More" search features active hain. Aap page-by-page infinite leads scan kar sakte hain jo single view table par accumulate hoti hain.

9. **Smart Database Auto-Cleanup (Startup Optimizer):**
   - Startup par background automatic clean-up routine chalta hai jo database storage optimize rakhta hai:
     - **Contacted leads** hamesha secure rehte hain.
     - 14 din se purane uncontacted leads flush ho jate hain.
     - 7 din se purane IGNORE priority leads clean ho jate hain.

10. **One-Click Excel Export (Premium Format):**
    - Dynamic column widths adjustments aur auto-formatted text column configurations ke saath seamless `.xlsx` download.

11. **Premium Modern Dark UI (Wow Aesthetics - BUG-13 Orange Accent):**
    - High-quality visual glassmorphism design.
    - Added a beautiful, dedicated **Orange Accent Card** (`stat-card orange`) for **Broken Websites** statistics. Iska top-border highlight aur hover shadow glow complete layout ko flawless visual distinctiveness deta hai.

12. **Smart Portfolio Scraper & Keyword Matcher (Dynamic Outreach):**
    - Settings mein apna portfolio URL (e.g. `https://raunaksharmaq64.github.io/portfolio/`) save karein. Backend automatically page ko scrape karke saare projects aur unke live demo links extract kar lega.
    - WhatsApp dynamic templates mein **`{project_sample}`** variable ke zariye matching engine (Gym, Hotel/Restaurant, Hostel/PG) dynamically sabse best-fit project demo link outreach message mein append kar deta hai.

13. **Gemini AI Outreach Personalization Writer (Hinglish Elite Persona):**
    - Settings mein optional **Gemini API Key** save karein.
    - **Broken Website Hook:** Agar lead ki website broken hai, toh AI pitch generator dynamically pivot ho jata hai aur client ke reviews ko appreciate karte hue unhe point out karta hai ki unki listed website abhi down/error page show kar rahi hai. Ek professional draft home mockup layout offer karke response rate 10x badha deta hai!
    - **0-Reviews Authentic Formatting (BUG-7 Fix):** Agar kisi business ki zero reviews hain, toh outreach text smart tarike se `"0 reviews"` (ya custom local lines) create karta hai instead of writing spammy terms like `"many reviews"`.

---

## 🔌 Tech Stack & Integrations

- **Backend:** Python 3.8+ + Flask
- **Frontend:** Responsive HTML5, Vanilla CSS3 (Glassmorphism design, transitions & micro-animations), Modern Javascript (DOM state handles, async fetch control)
- **Database:** SQLite3 (Local storage with dynamic backward-compatible schema migrations)
- **Libraries:**
  - `phonenumbers` (Google's port for phone validation)
  - `requests` (Stateless HTTP clients)
  - `pandas` & `openpyxl` (Premium Excel writing engines)
  - `serpapi` (Google Search & Maps integrations)

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
│   ├── serpapi_collector.py   # SerpApi engine implementation for Google Maps searches
│   └── google_maps_collector.py # Places API (New) engine integration
│
├── utils/                     # Smart text processing utility systems
│   ├── data_cleaner.py        # Duplicate remover, contact info cleaner, and scoring validator
│   ├── whatsapp.py            # Phone prependers and dynamic templates writer
│   ├── portfolio.py           # Smart HTML portfolio scraper and keyword matcher
│   └── ai_writer.py           # Elite Gemini AI sales pitch generator
│
├── templates/                 # UI View System
│   └── index.html             # High-end desktop user-dashboard template
│
└── static/                    # Dynamic Design and Dashboard controller files
    ├── css/
    │   └── style.css          # Core CSS styling system, orange stat-cards, and glassmorphism
    └── js/
        └── app.js             # State managers, outreach launchers, HTML escaping, and API fetches
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

---
*Developed with love for high-speed local business outreach, visual excellence, and secure B2B conversions.* 🎯
