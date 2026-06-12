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
   - **Broken Site Detection:** Har lead ke website status ko parallel check karta hai (HEAD request fallback to GET). Agar website open nahi hoti (404, 500, ya net error), toh use **🔴 HIGH Priority (⚠️ Broken Website)** badge de diya jata hai.
   - **Timeout Protection:** Strict 3s per-request limits lagayi gayi hain bina kisi global timeout abort risk ke, jisse checking bulletproof aur false-positive free ho jati hai.

3. **High-Accuracy Phone Validator Engine (Google Libphonenumber):**
   - Regex processing ko replace karke industry-grade **Google `phonenumbers` library** integrate ki gayi hai.
   - **Line Classification:** Numbers ko standardize (+91 for India) karke unhe `MOBILE`, `LANDLINE`, ya `UNKNOWN` mein classify karta hai.
   - **WhatsApp Prevention:** Agar business number Landline hai, toh WhatsApp buttons ko dynamically gray-out aur disable kar deta hai with a custom tooltip: *"Landline Number (No WhatsApp)"*, jisse manual outreach effort aur clicks bilkul waste nahi hote!

4. **Asynchronous Background Search Engine:**
   - Tasks background execution system ke zariye run hote hain jo user ko real-time progress update provide karte hain jabki browser UI unblocked rehta hai.
   - Dynamic search progress polling runs securely every 1.5 seconds.

5. **Intelligent Lead Filtering & Priority Scoring:**
   - **Ignore Active Websites:** Jin businesses ki website sahi chal rahi hai, unhe automatically IGNORE kar diya jata hai.
   - **Broken Websites Bumping:** Jin businesses ki listed website broken hai, unhe goldmine samajh kar instantly **HIGH** priority score ranking de di jati hai!
   - **Smart Scoring Badges:**
     - 🔴 **HIGH Priority:** No Website (or Broken Website!) + Low Reviews (<50). Perfect target clients.
     - 🟡 **MEDIUM Priority:** No Website + Moderate Reviews (50-200). Achi local brand par digital presence absent.
     - 🟢 **LOW Priority:** No Website + High Reviews (>200). Bare brands with massive customer volumes.

6. **Sanitized CSV Lead Importer:**
   - Bulk leads data upload support. `.csv` file upload karke phone numbers standardize karein, invalid emails clean karein, aur automatically priority score calculate karein!
   - Auto-generates fallback UUID place IDs for manual/imported leads to prevent database conflicts.

7. **GDPR Compliance & Data Portability:**
   - **Data Portability:** Ek click mein apna sara data (user registry, leads, search history, message logs) structure format mein JSON format mein export karein.
   - **Right to be Forgotten:** "Delete My Account" option ke zariye user account ke sath-sath usse linked leads, history aur outreach log records cascade deletes ke sath complete clean-up ho jaate hain.

8. **Secure Email + Password Authentication with OTP Reset & Welcome Emails:**
   - **Email Sign-In:** Login system ko Username se migrate karke **Email + Password** par shift kiya gaya hai. Usernames ko display name ki tarah treat kiya jata hai aur same username se multiple accounts create ho sakte hain.
   - **Contact Details Collection:** Signup ke samay user ka active Contact Number (phone) save kiya jata hai.
   - **Forgot Password OTP Recovery:** 6-digit One-Time Password (OTP) validation system ke zariye secured password reset logic.
   - **Automated Onboarding Welcome Emails:** Signup karte hi system background thread me user ke inbox par onboarding guidance mail send karta hai.

9. **Centralized Admin Dashboard Panel:**
   - Role-based control grid. `is_admin = true` accounts se login karne par header mein dynamic access icon (`👑`) dikhta hai jahan se server accounts (Users deactivation/activation, Admin promotions) aur global statistics manage ho paati hain.
   - Safety guards integrated: Admin accounts khud ko deactivate nahi kar sakte na hi khud ki admin privileges revoke kar sakte hain.

9. **Multi-Language AI Outreach Copywriter selection:**
   - Pitch copy translation capabilities. **Hinglish**, **English**, aur **Hindi** settings support dynamically. AI automatically language rules apply karke output custom generate karega.

10. **XSS Sanitization & Security Guards (BUG-8 Protection):**
    - High-grade front-end HTML escaping utility integrate ki gayi hai jo `&`, `<`, `>`, `"`, aur `'` ko fully sanitize karti hai.
    - Tooltips, business addresses, aur details securely render hoti hain bina kisi attribute breakout ya DOM XSS threat ke.

11. **Instagram & Facebook Social Scanner (On-Demand):**
    - SerpApi organic search engine ka use karke ek click mein specific business ke active **Instagram** aur **Facebook** profiles ko Google par scan karein.
    - Precision filters use hote hain taaki tags, reels, posts, ya sharing links ko filter out karke direct profiles hi milein.

12. **Instagram DM Link & Pitch Auto-Copy (100% Safe):**
    - Instagram DM button click karne par personalized outreach pitch automatically aapke system clipboard par copy ho jati hai aur unka profile browser window mein launch ho jata hai.
    - **Safety First:** Zero API bans! Kisi auto-bot APIs ka use nahi kiya gaya hai jo aapke Instagram accounts block kar sakein.

13. **Next-Page Pagination (Load More Leads):**
    - Index-offset pagination system ke zariye dynamic "Load More" search features active hain. Aap page-by-page infinite leads scan kar sakte hain jo single view table par accumulate hoti hain.

14. **Smart Database Auto-Cleanup (Startup Optimizer):**
    - Startup par background automatic clean-up routine chalta hai jo database storage optimize rakhta hai:
      - **Contacted leads** hamesha secure rehte hain.
      - 14 din se purane uncontacted leads flush ho jate hain.
      - 7 din se purane IGNORE priority leads clean ho jate hain.

15. **One-Click Excel Export (Premium Format):**
    - Dynamic column widths adjustments aur auto-formatted text column configurations ke saath seamless `.xlsx` download.

16. **Premium Modern Dark UI (Wow Aesthetics - BUG-13 Orange Accent):**
    - High-quality visual glassmorphism design.
    - Added a beautiful, dedicated **Orange Accent Card** (`stat-card orange`) for **Broken Websites** statistics. Iska top-border highlight aur hover shadow glow complete layout ko flawless visual distinctiveness deta hai.

17. **Smart Portfolio Scraper & Keyword Matcher (Dynamic Outreach):**
    - Settings mein apna portfolio URL (e.g. `https://raunaksharmaq64.github.io/portfolio/`) save karein. Backend automatically page ko scrape karke saare projects aur unke live demo links extract kar lega.
    - WhatsApp dynamic templates mein **`{project_sample}`** variable ke zariye matching engine (Gym, Hotel/Restaurant, Hostel/PG) dynamically sabse best-fit project demo link outreach message mein append kar deta hai.

18. **Gemini AI Outreach Personalization Writer (Hinglish Elite Persona):**
    - Settings mein optional **Gemini API Key** save karein.
    - **Broken Website Hook:** Agar lead ki website broken hai, toh AI pitch generator dynamically pivot ho jata hai aur client ke reviews ko appreciate karte hue unhe point out karta hai ki unki listed website abhi down/error page show kar rahi hai. Ek professional draft home mockup layout offer karke response rate 10x badha deta hai!
    - **0-Reviews Authentic Formatting (BUG-7 Fix):** Agar kisi business ki zero reviews hain, toh outreach text smart tarike se `"0 reviews"` (ya custom local lines) create karta hai instead of writing spammy terms like `"many reviews"`.

---

## 🔌 Tech Stack & Integrations

- **Backend:** Python 3.11+ + Flask (Thread-safe connection pooling, modular routing design)
- **Caching:** Flask-Caching (using SimpleCache storage engine)
- **Frontend:** Responsive HTML5, Vanilla CSS3 (Glassmorphism design, transitions & micro-animations), Modern Javascript (ESModules design, DOM state handles, async fetch control)
- **Database:** PostgreSQL (with thread-safe connection pooling, modular index structures, and foreign keys cascade deletes)
- **Containerization & DevOps:** Docker + Docker Compose, automated CI test validations using GitHub Actions
- **Libraries:**
  - `phonenumbers` (Google's port for phone validation)
  - `requests` (Stateless HTTP clients)
  - `pandas` & `openpyxl` (Premium Excel writing engines)
  - `serpapi` (Google Search & Maps integrations)
  - `psycopg2` (PostgreSQL adapter for Python)

---

## 📂 Project Directory Structure

```
ai_agent/
├── app.py                      # Main Flask app, modular blueprint registry, and auth middleware
├── database.py                 # Thread-safe database managers, pg pools, schema builders
├── requirements.txt            # Python environment packages specification
├── Dockerfile                  # Slim production Docker builder using Gunicorn
├── docker-compose.yml          # Container configuration orchestrating web (Flask) & db (Postgres)
├── config.py                   # Environment configurations management
├── constants.py                # Pipeline limits and service metadata configurations
├── .env                        # Secret environment variables configuration
├── .env.example                # Template file for secret configurations
├── .gitignore                  # Excluded directories and .env files registry
├── README.md                   # Detailed Hinglish guidelines & overview
│
├── routes/                     # Blueprint controllers
│   ├── auth.py                 # Login tracker locks and user auth endpoints
│   ├── dashboard.py            # Static preview servers and legal terms routers
│   ├── api_leads.py            # Asynchronous search status endpoints & CSV Importer
│   ├── api_outreach.py         # WhatsApp templates and Gemini email pitches compilers
│   ├── api_config.py           # GDPR data exporters, clear DB utilities, and Admin toggle controls
│   └── errors.py               # Custom error handlers (404, 403, 500, etc.)
│
├── collectors/                 # Core Data Extraction logic
│   ├── base_collector.py       # Abstract blueprint base model for future platforms integration
│   ├── serpapi_collector.py    # SerpApi engine implementation for Google Maps searches
│   └── google_maps_collector.py # Places API (New) engine integration
│
├── utils/                      # Smart text processing utility systems
│   ├── data_cleaner.py         # Duplicate remover, contact info cleaner, and scoring validator
│   ├── whatsapp.py             # Phone prependers and dynamic templates writer
│   ├── portfolio.py            # Smart HTML portfolio scraper and keyword matcher
│   ├── ai_writer.py            # Elite Gemini AI multi-language sales pitch generator
│   └── decorators.py           # Admin roles verification routing wrapper
│
├── templates/                  # UI View System
│   ├── index.html              # High-end desktop user-dashboard template
│   ├── admin.html              # Central control panel grid template
│   ├── terms.html              # Responsive dark legal terms of service static page
│   ├── privacy.html            # Static dark privacy policy page
│   ├── login.html              # Glassmorphic auth portal
│   └── signup.html             # User registration template
│
└── tests/                      # Testing verification suite
    ├── conftest.py             # App testing client configurations and clean DB setup
    ├── test_api_leads.py       # Leads pipeline status endpoints testing routines
    ├── test_auth.py            # Security auth locks and registration validation testing routines
    ├── test_database.py        # Schema migrators and isolation testing routines
    ├── test_perf.py            # Async runners and pagination page offset tests
    └── test_polish.py          # CSV parser, cascading deletes, admin toggles, and language checks
```

---

## 🚀 Setup & Installation (Hinglish Guide)

Follow steps to set up this premium lead finder tool in your local workspace:

### Run Locally (Manual Setup)

#### 1. Repository Clone or Directory Navigation
Sabse pehle project directory ko command line par open karein:
```bash
cd "c:\Users\Sahil\Desktop\ai agents"
```

#### 2. Install Python Dependencies
Requirements list me add kiye gaye packages ko install karein (requires Python 3.11+):
```bash
pip install -r requirements.txt
```

#### 3. API Key & SMTP setup in Environment
`env` configuration ke liye workspace mein `.env` file banayein ya `.env.example` ko copy karke save karein. 
Isme apni SerpApi key, Postgres DB details aur **System SMTP server configurations** input karein:
```env
SERPAPI_KEY=your_serpapi_private_key_here
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/leadhunter_db

# System SMTP details (Gmail / custom SMTP for OTP and onboarding mails)
SYSTEM_SMTP_HOST=smtp.gmail.com
SYSTEM_SMTP_PORT=465
SYSTEM_SMTP_EMAIL=your_system_email@gmail.com
SYSTEM_SMTP_PASSWORD=your_16_character_gmail_app_password
SYSTEM_SMTP_USE_SSL=true
```
*(Note: Gmail settings ke liye normal password ki jagah Google Security panel se generated 16-character App Password use karein. SerpApi key ko aap direct dashboard settings se bhi dynamically update kar sakte hain jo automatically `.env` par persist ho jaati hai).*

#### 4. Run the Application
Start the Flask dev server:
```bash
python app.py
```
Iske baad server running message dikhega and you can open:
👉 **[http://localhost:5000](http://localhost:5000)** inside your browser!

---

### Run Using Docker Compose (Recommended)

Aap single command ke zariye complete system (Flask app server + Postgres Database instance) configure kar sakte hain:
```bash
docker-compose up --build -d
```
Docker automatically local images pull karega, parameters bind karega aur server active status `/health` par verify kar lega!

---

### Run Automated Test Suite
Sare unit aur integration tests run karne ke liye pytest trigger karein:
```bash
.venv\Scripts\pytest tests/ -v
```

to start server :  .venv\Scripts\python app.py


---
*Developed with love for high-speed local business outreach, visual excellence, and secure B2B conversions.* 🎯
