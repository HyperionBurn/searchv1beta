# Competitive Intelligence Report: Recruiter Contact Finder Tools
## Generated: May 2, 2026
## Last Updated: May 2, 2026 — UAE/GCC Email Patterns & Technical Considerations Added

---

## CATEGORY 1: Recruiter-Specific Contact Tools (Tools SPECIFICALLY for Finding Recruiter Info)

### 1. hireEZ (formerly Hiretual)
- **URL**: https://hireez.com
- **What it does**: AI-powered talent sourcing platform. Reverse-engineers recruiter search — helps find recruiters by title, company, specialty. Has a Chrome extension that enriches LinkedIn profiles with contact info (email, phone).
- **Free tier**: Limited free Chrome extension (basic profile views). No free API. Paid plans start at ~$169/seat/mo.
- **Key differentiating feature**: AI-powered "Talent Signal" detects when candidates (including recruiters) are likely to change jobs. Can filter by "recruiter" job title across 800M+ profiles.
- **Can we learn/integrate**: Their approach to aggregating recruiter profiles from multiple sources + cross-referencing LinkedIn, GitHub, and conference speaker lists is worth studying.
- **Relevance**: 8/10

### 2. SeekOut
- **URL**: https://seekout.com
- **What it does**: Agentic AI recruiting platform. 1B+ candidate profiles. Has specific "Recruiter" filters to find sourcers/recruiters by specialty (tech recruiting, executive search, etc.).
- **Free tier**: **14-day free trial** with 500 contact credits + 1,000 exports. No credit card required. After trial, Recruit Lite is $2,150/yr.
- **Key differentiating feature**: "SeekOut Sam" — free AI sourcing agent. "SeekOut Spot" — outcome-based AI recruiting. Can search by security clearance, healthcare specialty. MCP server available for AI agent integration.
- **Can we learn/integrate**: Their MCP server integration pattern (https://seekout.com/solutions/mcp) is directly relevant. Their 14-day trial with generous credits is a model for user acquisition.
- **Relevance**: 9/10

### 3. Gem (formerly Gem Sourcing)
- **URL**: https://gem.com
- **What it does**: All-in-one recruiting platform (ATS + CRM + Sourcing + Outreach). Has sourcing tools that find recruiter contact info.
- **Free tier**: **Startups plan**: First 6 months FREE, then 50% off first paid year ($135/mo for 1-10 FTE). No free tier beyond that.
- **Key differentiating feature**: AI Outbound Sourcing, AI Talent Rediscovery, AI Fraud Detection. Unified ATS+CRM means all recruiter interactions are tracked end-to-end.
- **Can we learn/integrate**: Their "Talent 360 Profile" concept — enriching a person's profile from multiple data sources into a single view. Also their startup program is clever for user acquisition.
- **Relevance**: 7/10

### 4. Entelo (now part of Harmony Healthcare IT)
- **URL**: https://entelo.com (redirects/acquired)
- **What it does**: Was a talent sourcing platform with "Envoy" AI that predicted candidate job-change likelihood. Had strong diversity sourcing filters.
- **Free tier**: No free tier. Was enterprise-only (~$500+/mo).
- **Key differentiating feature**: "Track" feature monitored when specific recruiters/candidates changed jobs. Had "Snap" for email outreach automation.
- **Can we learn/integrate**: Their "predictive quit" signal — monitoring when recruiters leave agencies — could help identify independent recruiters. Their data model for people profiles is worth studying.
- **Relevance**: 5/10 (partially acquired/shuttered)

### 5. AmazingHiring
- **URL**: https://amazinghiring.com
- **What it does**: Sourcing tool that finds tech candidates (and recruiters) across 50+ sources — GitHub, StackOverflow, LinkedIn, Kaggle, etc. Shows cross-referenced profiles with contact info.
- **Free tier**: No public free tier. Custom pricing only. Chrome extension may have limited free features.
- **Key differentiating feature**: Cross-references a person's profiles across GitHub, LinkedIn, StackOverflow, Kaggle, and more — building a composite contact card. Shows technical assessment of candidates.
- **Can we learn/integrate**: Their cross-referencing approach (linking GitHub username → LinkedIn → email) is exactly what a CLI tool should do. Their profile aggregation logic is the gold standard.
- **Relevance**: 10/10 — their cross-source aggregation pattern is the #1 thing to learn

### 6. Hiretual (rebranded to hireEZ — see #1)

### 7. SourceWhale
- **URL**: https://www.sourcewhale.com
- **What it does**: Recruitment sourcing and outreach automation. Finds candidate contact info from LinkedIn profiles.
- **Free tier**: No free tier. Paid plans start around $99/mo.
- **Key differentiating feature**: Integrates directly with Bullhorn, Vincere, Erecruit — pulls contact data into existing recruiter CRMs.
- **Can we learn/integrate**: Their approach of enriching LinkedIn profiles with verified email/phone from multiple data providers in a waterfall pattern.
- **Relevance**: 6/10

---

## CATEGORY 2: Sales Prospecting Tools with Free Tiers

### 8. Reply.io
- **URL**: https://reply.io
- **What it does**: Multichannel sales engagement platform with built-in B2B database, email finder, and Chrome extension.
- **Free tier**: **14-day free trial** with full feature access (B2B database, email finder extension, multichannel sequences, API, AI features). No permanent free tier after trial. Starts at $49/user/mo.
- **Key differentiating feature**: "Jason AI SDR" — fully autonomous AI sales development rep. Also has "Live Data" credits for real-time contact enrichment. 1B+ B2B contacts database. MCP server integration.
- **Can we learn/integrate**: Their waterfall enrichment approach (checking multiple providers in sequence). Their Chrome extension architecture for in-page contact finding.
- **Relevance**: 7/10

### 9. Snov.io
- **URL**: https://snov.io
- **What it does**: All-in-one sales platform — email finder, verifier, drip campaigns, CRM. Has Chrome extension for finding emails on LinkedIn.
- **Free tier**: Trial plan with limited credits (50 credits). Starter plan at $29.25/mo for 1,000 credits. 7-tier email verification included.
- **Key differentiating feature**: Includes LinkedIn Prospect Finder extension, unlimited team seats on all plans, and built-in email warm-up. "Provider matching" — matches email domains to avoid spam filters.
- **Can we learn/integrate**: Their 7-tier email verification system. Their credit-based pricing model. Their LinkedIn Chrome extension approach.
- **Relevance**: 8/10

### 10. Lemlist
- **URL**: https://lemlist.com
- **What it does**: Multichannel outreach platform with 600M+ lead database, email/phone finder, LinkedIn automation.
- **Free tier**: **14-day free trial** of Multichannel Expert plan. No credit card required. After trial, account stays but can't send new campaigns. Starts at $63/user/mo.
- **Key differentiating feature**: "Find emails & phone numbers" — pay-per-success with rechargeable credits ($0.01/credit). 5 credits/email, 20 credits/phone. Intent signals (company visited your website, hiring signals, funding signals).
- **Can we learn/integrate**: Their pay-per-success credit model. Their intent signal monitoring (hiring signals are specifically useful for finding active recruiters). Their phone number finder (20 credits = $0.20/phone).
- **Relevance**: 8/10 — intent signals for recruiter hiring activity is valuable

### 11. Woodpecker
- **URL**: https://woodpecker.co
- **What it does**: Cold email + outreach platform. Focuses on deliverability and personalization.
- **Free tier**: 14-day free trial. No permanent free tier. Starts at $29/mo (cold email) or $54/mo (multichannel).
- **Key differentiating feature**: Best-in-class deliverability testing. Strong "Agency" mode for managing multiple client campaigns.
- **Can we learn/integrate**: Their deliverability-focused approach (Bounce Shield, email warm-up). Less relevant for contact finding, but their email verification is worth noting.
- **Relevance**: 4/10

### 12. Outreach.io
- **URL**: https://outreach.io
- **What it does**: Enterprise sales engagement platform. Sequence-based outreach with AI.
- **Free tier**: No free tier. Enterprise-only pricing (~$100+/user/mo).
- **Key differentiating feature**: "Kaia" AI meeting assistant. Strongest enterprise deal intelligence.
- **Can we learn/integrate**: Their "deal intelligence" concept — understanding the full buyer journey. Not directly relevant for contact finding.
- **Relevance**: 3/10

### 13. Salesloft
- **URL**: https://salesloft.com
- **What it does**: Sales engagement platform with AI-powered prospecting and outreach.
- **Free tier**: No free tier. Enterprise-only pricing.
- **Key differentiating feature**: "Drift" conversational marketing integration. Strong analytics.
- **Can we learn/integrate**: Minimal relevance for contact finding.
- **Relevance**: 3/10

---

## CATEGORY 3: OSINT Frameworks (Beyond SpiderFoot/theHarvester)

### 14. Maigret ⭐ (HIGH VALUE)
- **URL**: https://github.com/soxoj/maigret
- **What it does**: Collects a dossier on a person by username from **3000+ sites**. Far more comprehensive than Sherlock. Generates detailed PDF reports.
- **Free tier**: Fully free, open-source.
- **Key differentiating feature**: Searches 3000+ sites (vs Sherlock's 400). Can search by name, email, phone, IP in addition to username. Generates detailed PDF/HTML reports. Many sites return additional personal info (real name, photo, location, etc.)
- **Can we learn/integrate**: **This is the #1 tool to integrate.** It already does username-to-profile linking across 3000+ sites. We could pipe its output into our email/phone extraction. Its module system for adding new sites is well-architected.
- **Relevance**: 10/10

### 15. Recon-ng
- **URL**: https://github.com/lanmaster53/recon-ng
- **What it does**: Modular web reconnaissance framework. Has modules for email harvesting, contact finding, social media enumeration.
- **Free tier**: Fully free, open-source.
- **Key differentiating feature**: Modular architecture like Metasploit but for OSINT. Has marketplace for community modules. Scriptable with Python.
- **Can we learn/integrate**: Its modular plugin architecture. Each data source is an independent module. This is exactly the architecture we should use.
- **Relevance**: 7/10

### 16. Maltego (Community Edition)
- **URL**: https://maltego.com
- **What it does**: Visual link analysis platform. Maps relationships between people, email addresses, phone numbers, social media, domains.
- **Free tier**: **Maltego CE** — free community edition with limited transforms (data source queries). No recruiter-specific modules.
- **Key differentiating feature**: Visual graph-based relationship mapping. "Transform Hub" with 100+ data integrations. Can see connections between email → domain → company → recruiter → LinkedIn.
- **Can we learn/integrate**: Their graph-based data model for linking people to contact info. Their "transform" concept (each data source is a transformation applied to an entity).
- **Relevance**: 6/10

### 17. IntelOwl
- **URL**: https://github.com/intelowlproject/IntelOwl
- **What it does**: Threat intelligence platform that aggregates results from multiple analyzers (VirusTotal, Shodan, etc.). Can be repurposed for people intelligence.
- **Free tier**: Fully free, open-source. Self-hosted.
- **Key differentiating feature**: Centralized analysis — submit an email/username/domain and get results from 100+ analyzers simultaneously. REST API + web UI.
- **Can we learn/integrate**: Their analyzer aggregation pattern — submitting one query and fan-out to multiple data sources. Their API design is clean.
- **Relevance**: 7/10

### 18. BBOT (Big Brother OSINT Tool) ⭐
- **URL**: https://github.com/blacklanternsecurity/bbot
- **What it does**: Recursive internet scanner. Given a target, it recursively discovers related entities (subdomains, emails, people, etc.).
- **Free tier**: Fully free, open-source.
- **Key differentiating feature**: Recursive discovery — finds email from domain, then discovers more from that email, etc. Outputs to Neo4j for graph visualization. Has modules for Hunter.io, GitHub, Social media, etc.
- **Can we learn/integrate**: Their recursive discovery pattern is powerful — start with a company name, find all email patterns, then find all people with those patterns. Their Neo4j output format.
- **Relevance**: 8/10

### 19. Sn0int
- **URL**: https://github.com/kpcyrd/sn0int
- **What it does**: Semi-automatic OSINT framework and package manager. Focuses on discovering related entities (domains, IPs, emails, usernames).
- **Free tier**: Fully free, open-source. Written in Rust.
- **Key differentiating feature**: Package manager for OSINT modules (like npm but for recon scripts). Written in Rust — very fast. Lua scripting for custom modules.
- **Can we learn/integrate**: Their package management concept for OSINT modules. Their fast, concurrent architecture.
- **Relevance**: 6/10

### 20. Mr.Holmes
- **URL**: https://github.com/Lucksi/Mr.Holmes
- **What it does**: Complete OSINT tool with GUI. Email finding, username search, geolocation, social media search.
- **Free tier**: Fully free, open-source.
- **Key differentiating feature**: Web-based GUI for OSINT. Built-in email search, username checker, geolocation. Simple to use for non-technical users.
- **Can we learn/integrate**: Their web UI pattern for presenting OSINT results. Their email search module.
- **Relevance**: 5/10

### 21. GoSearch
- **URL**: https://github.com/ibnaleem/gosearch
- **What it does**: Search anyone's digital footprint across 300+ websites. Similar to Sherlock but in Go.
- **Free tier**: Fully free, open-source.
- **Key differentiating feature**: Written in Go — much faster than Python-based tools. 300+ websites.
- **Can we learn/integrate**: Their speed optimization. Their site list management.
- **Relevance**: 6/10

### 22. Seekr (OSINT)
- **URL**: https://github.com/seekr-osint/seekr
- **What it does**: Multi-purpose OSINT toolkit with web interface. Email OSINT, GitHub OSINT, people search.
- **Free tier**: Fully free, open-source.
- **Key differentiating feature**: Web interface with multiple OSINT tools integrated. Written in Go + TypeScript.
- **Can we learn/integrate**: Their web interface pattern for aggregating multiple OSINT tools.
- **Relevance**: 5/10

---

## CATEGORY 4: Contact Enrichment APIs (Beyond What We Have)

### 23. Tomba.io
- **URL**: https://tomba.io
- **What it does**: Email finder and verifier. Domain search, email finder by name+company, email verifier, author finder (find email from article URL).
- **Free tier**: **25 free searches/month**. Paid starts at $39/mo for 1,000 searches. CLI tool available (Go-based).
- **Key differentiating feature**: "Author Finder" — paste an article URL and find the author's email. Very useful for finding recruiter blog posts and extracting their email. Has a CLI tool (`tomba` command). Also has ChatGPT plugin.
- **Can we learn/integrate**: Their author finder API. Their CLI tool architecture. Their free tier is usable for testing.
- **Relevance**: 8/10

### 24. LeadMagic
- **URL**: https://leadmagic.io
- **What it does**: B2B data enrichment — email finder, phone finder, company intelligence, LinkedIn enrichment, job change detection.
- **Free tier**: MCP server available. Check their site for trial.
- **Key differentiating feature**: **MCP server** for Claude/Cursor integration. Job change detection. 19 API tools including email finder, phone finder, company data, social profile enrichment.
- **Can we learn/integrate**: Their MCP server pattern — exposing B2B enrichment as MCP tools that AI agents can call. This is the modern integration pattern.
- **Relevance**: 9/10

### 25. Datalayer
- **URL**: https://datalayer.sh
- **What it does**: B2B data enrichment MCP server. Find work emails, phone numbers, company data, tech stacks, and **buying intent signals**. 60M companies, 300M contacts.
- **Free tier**: MCP server available. Has a free tier (check site for current limits).
- **Key differentiating feature**: **Buying intent signals** — shows WHO is researching specific topics. Tech stack detection for companies. Works with Claude, Cursor, Windsurf.
- **Can we learn/integrate**: Their intent signal approach — detecting when a company is hiring (and thus their recruiters are active). Their MCP server is open-source on GitHub.
- **Relevance**: 9/10

### 26. Enrow
- **URL**: https://enrow.fr
- **What it does**: B2B email finder. Finds verified professional emails from first name, last name, and company.
- **Free tier**: 20 free credits on signup. Paid starts at €39/mo for 500 credits.
- **Key differentiating feature**: French-based (GDPR compliant). Claims 97%+ accuracy. API-first approach.
- **Can we learn/integrate**: Their GDPR-compliant approach to email finding. Their accuracy-focused methodology.
- **Relevance**: 5/10

### 27. UpLead
- **URL**: https://uplead.com
- **What it does**: B2B contact database with email verification built-in. 155M+ contacts.
- **Free tier**: 5 free credits on signup. Paid starts at $99/mo for 250 credits.
- **Key differentiating feature**: Real-time email verification before download (95%+ accuracy guarantee). "Intent Data" add-on shows prospects actively researching specific topics.
- **Can we learn/integrate**: Their real-time verification before delivery pattern. Their intent data approach for identifying active recruiters.
- **Relevance**: 6/10

### 28. LeadGibbon
- **URL**: https://leadgibbon.com
- **What it does**: LinkedIn email finder Chrome extension. Find email from LinkedIn profile.
- **Free tier**: Limited free trial. Paid starts around $49/mo.
- **Key differentiating feature**: Direct LinkedIn integration — click on a recruiter's profile and get their email.
- **Can we learn/integrate**: Their Chrome extension pattern for LinkedIn enrichment.
- **Relevance**: 5/10

### 29. Clay (clay.com)
- **URL**: https://clay.com
- **What it does**: AI-powered enrichment waterfall platform. Query 75+ data providers in sequence to find the best contact info.
- **Free tier**: Limited free trial. Paid starts at $149/mo.
- **Key differentiating feature**: **Enrichment waterfalls** — queries Hunter, Apollo, Snov, Clearbit, etc. in sequence, picking the best result. This is the gold standard for contact enrichment.
- **Can we learn/integrate**: **Their waterfall enrichment pattern is THE key concept.** Query multiple providers in priority order, take the first verified result, fall back to the next provider. Open-source alternative: `enrichment-kit` on GitHub.
- **Relevance**: 10/10

### 30. Enrichment-Kit (Open Source Clay Alternative)
- **URL**: https://github.com/masteranime/enrichment-kit
- **What it does**: Open-source Clay.com alternative. Multi-vendor enrichment waterfalls. BYOK (Bring Your Own API keys).
- **Free tier**: Fully free, open-source. You pay only for the API keys you use (85% cheaper than Clay).
- **Key differentiating feature**: Implements the waterfall enrichment pattern for free. Supports Apollo, Hunter, SerpAPI, and more. TypeScript-based.
- **Can we learn/integrate**: **Directly relevant.** This is exactly the pattern we should use. Study their waterfall implementation and port the concept to Python.
- **Relevance**: 10/10

---

## CATEGORY 5: Chrome Extensions for Contact Finding (Beyond What We Know)

### 31. SeekOut Chrome Extension
- **URL**: https://seekout.com/chrome-extension
- **What it does**: Enriches LinkedIn profiles with contact info (email, phone). Part of SeekOut platform.
- **Free tier**: Available with SeekOut free trial (14 days, 500 credits).
- **Key differentiating feature**: AI-powered candidate matching from LinkedIn profiles. Shows candidate diversity info, GitHub profiles.
- **Relevance**: 7/10

### 32. Reply.io Chrome Extension
- **URL**: Available in Chrome Web Store
- **What it does**: Find contacts and enrich leads directly from LinkedIn, company websites.
- **Free tier**: Available with Reply.io free trial (14 days).
- **Key differentiating feature**: Direct integration with Reply's B2B database (1B+ contacts). Can start outreach sequences from the extension.
- **Relevance**: 5/10

### 33. Snov.io LinkedIn Prospect Finder
- **URL**: Part of Snov.io platform
- **What it does**: Find emails and phone numbers directly from LinkedIn profiles and Sales Navigator.
- **Free tier**: Available on all Snov.io paid plans (Starter at $29.25/mo). Trial includes limited credits.
- **Key differentiating feature**: Works on both LinkedIn and Sales Navigator. Team sharing of found contacts.
- **Relevance**: 6/10

### 34. Lusha
- **URL**: https://lusha.com
- **What it does**: Contact intelligence platform. Chrome extension for LinkedIn/company websites to find direct dial numbers and emails.
- **Free tier**: 5 free credits/mo. Paid starts at $36/user/mo (billed annually) for 480 credits/yr.
- **Key differentiating feature**: Best-in-class for **phone numbers** — claims highest accuracy for direct dial mobile numbers. Israeli company, strong data sourcing.
- **Can we learn/integrate**: Their phone number finding methodology. Their credit-based pricing with generous free tier is a good model.
- **Relevance**: 8/10

### 35. Name2Email
- **URL**: https://name2email.com
- **What it does**: Simple Chrome extension — type a person's name and domain, it guesses and verifies their email.
- **Free tier**: **Fully free** (maintained by Reply.io). No API key needed.
- **Key differentiating feature**: Dead simple — no login, no API key. Enter name + domain → get email. Works as a web tool too.
- **Can we learn/integrate**: **Their email guessing algorithm.** This is free and embeddable. Generate email permutations (firstname.lastname@domain, f.lastname@domain, etc.) and verify via SMTP.
- **Relevance**: 9/10

---

## CATEGORY 6: Open-Source People Search Engines

### 36. Mailfoguess ⭐
- **URL**: https://github.com/WildSiphon/Mailfoguess
- **What it does**: OSINT tool to guess and verify email addresses from firstname, middlename, lastname, username. Generates all possible email permutations and verifies them.
- **Free tier**: Fully free, open-source. Python-based.
- **Key differentiating feature**: Generates EVERY possible email permutation from name + domain, then verifies each via SMTP. Supports multiple domains simultaneously.
- **Can we learn/integrate**: **Directly useful.** Their email permutation generation algorithm and SMTP verification logic can be used as-is or adapted.
- **Relevance**: 9/10

### 37. MailFinder
- **URL**: https://github.com/mishakorzik/MailFinder
- **What it does**: OSINT tool for finding email by first and last name.
- **Free tier**: Fully free, open-source. Python-based.
- **Key differentiating feature**: Automated email search from just a name. Integrates with multiple search engines.
- **Can we learn/integrate**: Their search engine integration pattern for finding emails.
- **Relevance**: 7/10

### 38. skip-trace
- **URL**: https://github.com/WebOlivia/skip-trace
- **What it does**: People search and tracing API. Identity resolution, contact enrichment, phone lookup, email discovery.
- **Free tier**: Fully free, open-source. Python-based.
- **Key differentiating feature**: API-based skip tracing — finding people from minimal information. Identity resolution (linking different data points to one person).
- **Can we learn/integrate**: Their identity resolution logic. Their API design for people search.
- **Relevance**: 7/10

### 39. gofps (FastPeopleSearch Wrapper)
- **URL**: https://github.com/TAJ4K/gofps
- **What it does**: Wrapper for fastpeoplesearch.com — a people search engine. Reverse phone lookup, name lookup, address lookup.
- **Free tier**: Fully free, open-source. Go-based.
- **Key differentiating feature**: Programmatic access to FastPeopleSearch data (which includes phone numbers, emails, addresses, relatives).
- **Can we learn/integrate**: Their web scraping pattern for people search engines.
- **Relevance**: 6/10

### 40. Relay (Vaylo)
- **URL**: https://github.com/vaylocorp/Relay
- **What it does**: Open-source OSINT platform for discovering and correlating digital footprints from public sources. GDPR-aware.
- **Free tier**: Fully free, open-source. TypeScript-based.
- **Key differentiating feature**: GDPR-aware OSINT. Correlates digital footprints across multiple sources. Web-based UI.
- **Can we learn/integrate**: Their GDPR-compliant approach. Their correlation engine for linking data points.
- **Relevance**: 6/10

### 41. TheScrapper
- **URL**: https://github.com/champmq/TheScrapper
- **What it does**: Scrape emails, phone numbers, and social media accounts from any website.
- **Free tier**: Fully free, open-source. Python-based.
- **Key differentiating feature**: One-command website scraping for all contact info. Regex-based extraction of emails, phones, social links.
- **Can we learn/integrate**: Their regex patterns for extracting contact info from web pages.
- **Relevance**: 7/10

### 42. OptiCrawl
- **URL**: https://github.com/ChristopherPeacock/OptiCrawl
- **What it does**: CLI tool for automated lead generation. Extracts emails and contact info using Google Search via SerpAPI.
- **Free tier**: Fully free, open-source. Python-based. Requires SerpAPI key (100 free searches/mo).
- **Key differentiating feature**: Uses Google Search to find contact info — searches for "[name] email" or "[company] contact" patterns. Retro-styled CLI.
- **Can we learn/integrate**: Their Google Dork approach to finding contact info. Their SerpAPI integration.
- **Relevance**: 7/10

### 43. GitHub Email Finder
- **URL**: https://github.com/elliott-diy/EmailFinder
- **What it does**: CLI tool to fetch email addresses from GitHub commits by username.
- **Free tier**: Fully free, open-source. Python-based.
- **Key differentiating feature**: Extracts emails from GitHub commit history — recruiters who have open-source contributions will have their emails in git commit metadata.
- **Can we learn/integrate**: **Directly useful.** Git commits expose email addresses. If a recruiter has a GitHub account, we can find their email from their commit history.
- **Relevance**: 8/10

### 44. PeopleScraper
- **URL**: https://github.com/HelloByeLetsNot/PeopleScraper
- **What it does**: Python GUI tool that searches multiple search engines for a given first name, last name, and additional criteria.
- **Free tier**: Fully free, open-source. Python-based.
- **Key differentiating feature**: Multi-engine search with GUI. Clickable links to results.
- **Can we learn/integrate**: Their multi-engine search aggregation pattern.
- **Relevance**: 4/10

---

## CATEGORY 7: B2B Intent Data Platforms

### 45. 6sense
- **URL**: https://6sense.com
- **What it does**: B2B intent data platform. Shows which companies are researching specific topics (including "hiring", "recruitment", "talent acquisition").
- **Free tier**: No free tier. Enterprise pricing only (~$50K+/yr).
- **Key differentiating feature**: AI-powered buyer intent detection. Can identify when a company is actively hiring for specific roles — meaning their recruiters are active.
- **Can we learn/integrate**: Their intent signal concept — detecting hiring activity from job postings, website visits, content consumption patterns.
- **Relevance**: 6/10 (concept valuable, but enterprise pricing)

### 46. Bombora
- **URL**: https://bombora.com
- **What it does**: B2B intent data. Shows company-level research behavior across 16,000+ topics.
- **Free tier**: No free tier. Enterprise pricing.
- **Key differentiating feature**: "Surge" reports showing companies with unusually high research activity in specific topics (like "recruitment software" or "hiring").
- **Can we learn/integrate**: Their surge detection algorithm — identifying companies with anomalous hiring-related web activity.
- **Relevance**: 5/10

### 47. LeadMagic (see #24 — has intent signals)

### 48. Datalayer (see #25 — has buying intent signals)

### 49. Lemlist Intent Signals (see #10)
- Hiring & job change signals: From 100 credits ($1/signal)
- LinkedIn engagement signals: From 400 credits ($4/signal)
- Company fundraising signals: From 100 credits ($1/signal)

---

## CATEGORY 8: Recruiting CRM Platforms

### 50. Bullhorn
- **URL**: https://bullhorn.com
- **What it does**: #1 recruitment CRM/ATS for staffing agencies. 350+ marketplace integrations.
- **Free tier**: No free tier. Starter at $99/user/mo (1-2 users only). Core at $165/user/mo.
- **Key differentiating feature**: Has a public API (https://developer.bullhorn.com). Open API access for integrations. Some Bullhorn users have public career pages that list recruiter names and contact info.
- **Can we learn/integrate**: Their Open API could potentially be used to find public recruiter profiles. Their marketplace shows which enrichment tools integrate with recruiting CRMs.
- **Relevance**: 4/10

### 51. Manatal
- **URL**: https://manatal.com
- **What it does**: AI-powered recruitment software. Has Open API and MCP Server integration.
- **Free tier**: **14-day free trial**, no credit card required. Professional at $15/user/mo (up to 15 jobs). Enterprise at $35/user/mo.
- **Key differentiating feature**: **Has an MCP Server** for ChatGPT/LLM integration. Open API access. "People-Match AI" Chrome extension sources from 700M+ candidates. Finds phone numbers and emails of candidates.
- **Can we learn/integrate**: Their MCP server implementation. Their Chrome extension for sourcing contact info. Their pricing is the most accessible of all recruiting CRMs.
- **Relevance**: 7/10

### 52. Recruitee (now Tellent)
- **URL**: https://recruitee.com (now part of Tellent)
- **What it does**: Modern ATS with team collaboration. Career site builder.
- **Free tier**: 14-day free trial. No permanent free tier.
- **Key differentiating feature**: Public career pages often list hiring team members (recruiter names, photos). Their "careers site" feature exposes recruiter info.
- **Can we learn/integrate**: Scraping public career pages for recruiter names/roles.
- **Relevance**: 4/10

### 53. JobAdder
- **URL**: https://jobadder.com
- **What it does**: Recruitment CRM for agencies and in-house teams. Custom pricing only.
- **Free tier**: No free tier. Custom pricing based on team size and needs. Has API + Sandbox as add-on.
- **Key differentiating feature**: Strong API access (add-on). Broadbean integration for multi-channel job posting. 200+ app integrations.
- **Can we learn/integrate**: Their API structure for recruitment data.
- **Relevance**: 3/10

---

## CATEGORY 9: Email Verification Services

### 54. Verifalia
- **URL**: https://verifalia.com
- **What it does**: Email verification with multiple quality levels (Standard, High, Extreme). Disposable email detection. Free email provider detection.
- **Free tier**: **25 free verifications/day** (resets daily, no accumulation). Credits never expire in paid packs. Pay-as-you-go: 1,000 credits = $7.90.
- **Key differentiating feature**: Three quality levels (Standard, High, Extreme). "Extreme" verifies catch-all domains via actual email sending. Bot detection/CAPTCHA. SDKs for .NET, Go, Java, JavaScript, PHP, Ruby. Military-grade encryption.
- **Can we learn/integrate**: Their multi-level verification approach. Their free daily credits model is good for low-volume testing. Their SDK pattern.
- **Relevance**: 7/10

### 55. MillionVerifier
- **URL**: https://millionverifier.com
- **What it does**: Email verification with claimed 99%+ accuracy.
- **Free tier**: Check site for current trial offers. Bulk pricing: among the cheapest ($0.10/1K emails for large lists).
- **Key differentiating feature**: Best price-per-email at scale. Free EmailAcademy PRO access. Hungarian company, GDPR compliant.
- **Can we learn/integrate**: Their pricing model. Their accuracy methodology.
- **Relevance**: 5/10

### 56. DeBounce
- **URL**: https://debounce.com
- **What it does**: Email verification and list cleaning.
- **Free tier**: 100 free verifications on signup. Pay-as-you-go: 5,000 emails = $10.
- **Key differentiating feature**: Very cheap at scale. Simple API. Catch-all detection.
- **Can we learn/integrate**: Their simple API design. Their pay-as-you-go pricing model.
- **Relevance**: 6/10

### 57. Bouncer
- **URL**: https://bouncer.ai
- **What it does**: Email verification with deliverability testing.
- **Free tier**: Check site for trial. Competitive pricing at scale.
- **Key differentiating feature**: "Don't waste money on undeliverable leads" focus. Strong catch-all domain handling.
- **Can we learn/integrate**: Their catch-all domain verification approach.
- **Relevance**: 5/10

### 58. OmkarCloud Email Verification API (Open Source)
- **URL**: https://github.com/omkarcloud/email-verification-api
- **What it does**: REST API to verify email addresses for deliverability and get owner details (name, gender). Detects disposable emails and free providers.
- **Free tier**: Fully free, open-source. Self-hosted.
- **Key differentiating feature**: Open-source email verification with owner name detection. Returns gender and name from email. Real-time verification.
- **Can we learn/integrate**: **Directly useful.** Their SMTP verification logic. Their name extraction from email patterns.
- **Relevance**: 8/10

---

## CATEGORY 10: Phone Number Append Services

### 59. Lusha (see #34)
- **Best for phone numbers**: 5 free credits/mo. Claims highest accuracy for direct dial mobile numbers. ~$0.08-0.10/phone on paid plans.

### 60. Lemlist Phone Finder (see #10)
- **Pricing**: 20 credits/phone number = $0.20/phone. Pay per success.

### 61. Snov.io Phone Finder (see #9)
- **Pricing**: Part of credit system. Finder extension can extract phone numbers from LinkedIn.

### 62. Truecaller API
- **URL**: https://developer.truecaller.com
- **What it does**: Reverse phone lookup. Given a phone number, returns the owner's name and other details.
- **Free tier**: Limited API access for developers. Enterprise pricing for bulk lookups.
- **Key differentiating feature**: World's largest phone number database (3B+ numbers). Can identify spam numbers.
- **Can we learn/integrate**: Their reverse phone lookup API for verifying phone numbers found by other means.
- **Relevance**: 6/10

### 63. ClearoutPhone
- **URL**: https://clearout.io/phone-validator/
- **What it does**: Phone number validation and carrier detection. Verifies if phone numbers are valid, active, and identifies carrier/line type (mobile, landline, VoIP).
- **Free tier**: 100 free credits on signup. Paid: 5,000 phones = $44.
- **Key differentiating feature**: Line type detection (mobile vs landline vs VoIP). Carrier identification.
- **Can we learn/integrate**: Their phone validation API for verifying recruiter phone numbers.
- **Relevance**: 5/10

### 64. Numverify (via API)
- **URL**: https://numverify.com
- **What it does**: Phone number validation API. Formats, locates, and validates phone numbers globally.
- **Free tier**: 100 API requests/mo (free tier). Paid starts at $14.99/mo for 5,000 requests.
- **Key differentiating feature**: 232 countries supported. Returns carrier name, line type, location. Simple REST API.
- **Can we learn/integrate**: Their phone validation API for cleaning/verifying phone numbers. Generous free tier.
- **Relevance**: 7/10

---

## TOP 10 HIGHEST-VALUE FINDINGS (Ranked by What We Can Learn/Integrate)

| Rank | Tool | Why It's Critical |
|------|------|-------------------|
| 1 | **Maigret** (GitHub) | 3000+ site username search, free, generates complete dossiers. Our tool should pipe Maigret output into email/phone extraction. |
| 2 | **enrichment-kit** (GitHub) | Open-source Clay.com alternative — implements the waterfall enrichment pattern we need. Study and port to Python. |
| 3 | **AmazingHiring** | Cross-referencing profiles across GitHub/LinkedIn/StackOverflow is exactly our use case. Replicate their aggregation pattern. |
| 4 | **Name2Email** | Free, no-API-key email guessing from name+domain. Embed this logic directly. |
| 5 | **Mailfoguess** (GitHub) | Email permutation generation + SMTP verification. The core email finding algorithm. |
| 6 | **LeadMagic MCP** | MCP server pattern for exposing B2B enrichment as AI-agent-callable tools. Modern integration architecture. |
| 7 | **Datalayer MCP** | 60M companies, 300M contacts + intent signals via MCP. The buying intent signal concept. |
| 8 | **GitHub Email Finder** | Extract emails from git commit history. If a recruiter has a GitHub account, their email is in their commits. |
| 9 | **SeekOut** | 14-day free trial with 500 credits + 1,000 exports. Best free recruiter database access. MCP server available. |
| 10 | **BBOT** | Recursive discovery pattern (company → email patterns → people → more people). Their Neo4j graph output. |

---

## KEY PATTERNS TO IMPLEMENT (From This Research)

### Pattern 1: Waterfall Enrichment (from Clay/enrichment-kit)
```
Input: Name + Company
→ Query Provider A (Hunter.io free: 25/mo)
→ If no result, Query Provider B (Tomba free: 25/mo)
→ If no result, Query Provider C (Snov.io trial credits)
→ If no result, Email Permutation + SMTP Verify (free, local)
→ Return best result with confidence score
```
**Cost: Near-zero using free tiers combined**

### Pattern 2: Cross-Source Profile Aggregation (from AmazingHiring)
```
Input: Person Name or Username
→ Maigret: Search 3000+ sites for this username
→ GitHub: Check for account + extract email from commits
→ LinkedIn: Enrich with company, title, location
→ SpiderFoot: Run full OSINT scan
→ Cross-reference: Link all profiles to same person
→ Output: Unified contact card with email, phone, social links
```

### Pattern 3: Recruiter-Specific Discovery (from SeekOut/hireEZ)
```
Input: Company Name or Industry
→ Search job boards for "recruiter" at target company
→ Extract recruiter names from job postings
→ Find LinkedIn profiles for those recruiters
→ Enrich with email/phone via waterfall
→ Monitor for job changes (recruiter left company → independent)
```

### Pattern 4: Intent Signal Detection (from Lemlist/Datalayer)
```
Input: Target companies or industries
→ Monitor job boards for new postings (hiring signal)
→ Check company career pages for active recruiter listings
→ Detect when recruiters update LinkedIn profiles (job change)
→ Flag active recruiters for outreach
```

### Pattern 5: MCP Integration (from LeadMagic/Datalayer/Manatal)
```
Build our tool as an MCP server:
→ Tool: find_recruiter (company, title_filter)
→ Tool: enrich_contact (name, company)
→ Tool: verify_email (email)
→ Tool: verify_phone (phone)
→ Works with Claude, Cursor, Windsurf, and any MCP client
```

---

## FREE RESOURCES SUMMARY (Usable Without Payment)

| Resource | Free Allowance | What You Get |
|----------|---------------|--------------|
| Maigret | Unlimited | 3000+ site username search |
| SpiderFoot | Unlimited | 200+ OSINT modules |
| theHarvester | Unlimited | Email/domain harvesting |
| Sherlock | Unlimited | 400+ social network username search |
| BBOT | Unlimited | Recursive OSINT scanning |
| Mailfoguess | Unlimited | Email guessing + SMTP verify |
| Name2Email | Unlimited | Email guessing from name+domain |
| GitHub commit emails | Unlimited | Emails from git history |
| Hunter.io | 25/mo | Email finder + verifier |
| Tomba | 25/mo | Email finder |
| Verifalia | 25/day | Email verification |
| Numverify | 100/mo | Phone validation |
| Lusha | 5/mo | Phone + email finder |
| SeekOut trial | 14 days / 500 credits | Full recruiter database |
| OmkarCloud email verify | Unlimited (self-hosted) | Email verification + name extraction |

---

# CATEGORY 11: GCC/UAE Recruitment Agencies with Public Recruiter Directories

> **Purpose**: Catalog of every known GCC recruitment agency, focusing on which ones have **publicly accessible recruiter/staff directories with contact info** (email, phone, LinkedIn). These agencies *want* to be found — recruiter contact info is their marketing. A Python CLI tool should scrape or link to these directories.

---

## 11A. MAJOR INTERNATIONAL AGENCIES WITH UAE OFFICES

### 1. Hays Gulf (Hays Middle East)
- **URL**: https://www.hays.ae/
- **Specialties**: IT, Finance, Construction, Engineering, Oil & Gas, HR, Legal, Marketing, Sales, Healthcare, Education, Procurement, Supply Chain
- **UAE/GCC Offices**: Dubai (Al Thuraya Tower 1, Media City), Abu Dhabi (Guardian Tower), Riyadh (Saudi Arabia)
- **Public recruiter profiles?**: **NO individual recruiter profiles on website.** Office directory with general phone numbers only: +971 4 559 5800
- **How to access recruiters**: Search LinkedIn for "Hays" + "UAE" / "Dubai" / "Middle East" — recruiters list `@hays.com` emails. Individual consultant names appear in job postings. The website's "Our Expertise" section lists practice areas but not individual consultant names.
- **Relevance**: 7/10 — large agency with 50+ recruiters in UAE but no public directory; LinkedIn scraping required

### 2. Michael Page UAE (PageGroup)
- **URL**: https://www.michaelpage.ae/
- **Specialties**: Accounting & Finance, Banking, Engineering, HR, Legal, Marketing, Procurement, Retail, Sales, Secretarial, Strategy, Supply Chain, Technology
- **UAE/GCC Offices**: Dubai (DIFC, Al Fattan Currency House Tower), also serves Saudi Arabia, Qatar, Kuwait, Bahrain, Oman
- **Public recruiter profiles?**: **NO public recruiter directory on the main site.** The "About Us / Our Teams" section is behind login/dynamic content that doesn't list individual consultant profiles with emails.
- **How to access recruiters**: Each job posting lists a named consultant. LinkedIn search "Michael Page" + "Dubai"/"UAE" yields recruiters. General email pattern: `firstname.lastname@michaelpage.com`
- **Relevance**: 7/10 — major player with 40+ UAE recruiters; no public staff directory but individual names on job listings

### 3. Robert Half UAE
- **URL**: https://www.roberthalf.com/ae/en
- **Specialties**: Finance & Accounting, Technology, Admin/HR/Office Support, Legal, Financial Services
- **UAE/GCC Offices**: Dubai (DIFC). Regional hub serving UAE and wider GCC.
- **Public recruiter profiles?**: **NO public recruiter directory.** The UAE site is a thin regional page — it redirects to a UK/international page for team details. Phone: +44 207 331 2234 (UK number listed).
- **How to access recruiters**: LinkedIn search "Robert Half" + "Dubai"/"UAE". The website has a "Request Talent" form but no named consultants. Email pattern typically `firstname.lastname@roberthalf.com`
- **Relevance**: 5/10 — limited UAE-specific presence; no local recruiter directory; mainly finance/accounting focus

### 4. Robert Walters UAE (Middle East)
- **URL**: https://www.robertwalters.ae/
- **Specialties**: Accounting & Finance, Banking & Financial Services, HR & Business Support, Legal, Technology & Digital, Sales & Marketing, Luxury & Retail, Property & Construction, Saudi Arabia
- **UAE/GCC Offices**: Dubai, Abu Dhabi, Saudi Arabia (Riyadh). Over 25 years in the Middle East.
- **Public recruiter profiles?**: **PARTIAL — named consultants appear in "Our Stories" testimonials** (e.g., Omer, Anchal named with first names). Full consultant directory URL `/about-us/our-people.html` returned 404. The site has office contact pages (Dubai, Abu Dhabi, Saudi) but no browsable staff directory.
- **How to access recruiters**: Contact page has office phone numbers. Named consultants appear in candidate testimonials. LinkedIn search "Robert Walters" + "Dubai"/"Abu Dhabi" — recruiters typically use `@robertwalters.com` emails. General email: `contact@robertwalters.com`
- **Relevance**: 7/10 — strong UAE presence; partial name exposure through testimonials; no structured directory

### 5. Adecco Middle East
- **URL**: https://www.adecco.com/en-ae
- **Specialties**: IT & Telecom, Sales/Marketing, Banking/Finance/Fintech, Oil & Gas/Energy, Logistics, BPO/Customer Service, Retail, Hospitality, Manufacturing, Aviation, Engineering & Construction, Legal, Automotive, Public Sector
- **UAE/GCC Offices**: Dubai, Abu Dhabi. 62 countries, 3,800 locations globally.
- **Public recruiter profiles?**: **NO individual recruiter directory.** Contact is via forms and general email: `adeccoae.info@adecco.com`. Offers services including Emiratisation, Mass Recruitment, RPO, Executive Search, Payroll, Visa & PRO.
- **How to access recruiters**: LinkedIn search "Adecco" + "UAE"/"Dubai" — many recruiters listed. Large blue-collar/semi-skilled staffing operation (construction, hospitality, retail). Email pattern: `firstname.lastname@adecco.com`
- **Relevance**: 8/10 — massive UAE presence across all sectors including blue-collar; no public directory but high recruiter density on LinkedIn

### 6. ManpowerGroup Middle East
- **URL**: https://www.manpowergroup.ae/
- **Specialties**: Permanent Recruitment, Executive Search, Payroll Solutions, Outsourcing, Contingent Staffing, Talent Development
- **UAE/GCC Offices**: Dubai Internet City, Building 1, Office 204. 15+ years in GCC.
- **Public recruiter profiles?**: **NO public recruiter directory.** Phone: +971 4 391 0460. Email: `info@manpower-me.com`. Three brands under one roof: Manpower (staffing), Talent Solutions (RPO), Right Management (career transition).
- **How to access recruiters**: LinkedIn search "ManpowerGroup" OR "Manpower Middle East" + "UAE"/"Dubai". Active on LinkedIn, Facebook, Twitter.
- **Relevance**: 6/10 — significant GCC presence; no public directory; general contact only

### 7. Randstad UAE
- **URL**: https://www.randstad.ae/ (site issues — redirects/blocks)
- **Specialties**: General staffing, professional recruitment, executive search
- **UAE/GCC Offices**: Dubai (DIFC area)
- **Public recruiter profiles?**: **Unknown — website was inaccessible during research.** Randstad typically maintains consultant directories on their global sites.
- **How to access recruiters**: LinkedIn search "Randstad" + "UAE"/"Dubai"
- **Relevance**: 5/10 — global #2 staffing firm but UAE site accessibility issues limit utility

### 8. Kelly Services UAE
- **URL**: https://www.kellyservices.ae/ (redirects to global .com)
- **Specialties**: Engineering, IT, Science, Finance, Light Industrial
- **UAE/GCC Offices**: Regional presence but website redirects to global page — limited UAE-specific content
- **Public recruiter profiles?**: **NO UAE-specific recruiter directory.** Global site has some consultant pages.
- **Relevance**: 4/10 — limited UAE-specific digital presence

---

## 11B. REGIONAL / GCC-HEADQUARTERED AGENCIES

### 9. BAC Middle East (BAC Recruitment)
- **URL**: https://www.bacme.com/ (content extraction blocked — likely JS-heavy site)
- **Specialties**: Executive search, middle management, professional recruitment across all sectors
- **UAE/GCC Offices**: Dubai (established 1979 — one of the oldest GCC agencies). Covers UAE, Saudi, Qatar, Bahrain, Oman, Kuwait.
- **Public recruiter profiles?**: **LIKELY YES** — BAC historically has a "Meet the Team" page with consultant photos, bios, and direct contact info. The `/our-team` URL is standard. Could not confirm during research due to JS-rendered content.
- **How to access**: Navigate to https://www.bacme.com/ and look for "Our Team" or "Our Consultants" section. Try `https://www.bacme.com/our-team/`
- **Relevance**: 9/10 — oldest GCC agency; likely has structured consultant directory with direct contact info; HIGH priority for CLI tool scraping

### 10. Mackenzie Jones
- **URL**: https://www.mackenziejones.com/
- **Specialties**: Executive Recruitment, RPO Solutions
- **UAE/GCC Offices**: Dubai (UAE HQ)
- **Public recruiter profiles?**: **PARTIAL** — Website has "About" page and "Contact Us" but no visible public staff directory on main pages. They operate two divisions: Mackenzie Jones Recruitment and Mackenzie Jones RPO Solutions.
- **How to access recruiters**: Contact page at `/contact`. LinkedIn: `linkedin.com/company/mackenzie-jones-middle-east/`. Instagram: `@mackenziejonesdubai`. YouTube channel active.
- **Relevance**: 6/10 — well-known Dubai executive recruiter; no structured staff directory; LinkedIn/social media is primary contact channel

### 11. Charterhouse
- **URL**: https://www.charterhouseme.com/
- **Specialties**: Accounting, Finance, Banking, HR, IT, Legal, Marketing, Sales, Supply Chain, Engineering, Healthcare
- **UAE/GCC Offices**: Dubai, Abu Dhabi. Covers all GCC countries. One of the largest regional firms.
- **Public recruiter profiles?**: **LIKELY YES** — Charterhouse has historically maintained "Our Consultants" page with individual recruiter profiles by specialization. The URL `/our-consultants` returned content extraction issues (JS-heavy). They are known for naming consultants on job listings.
- **How to access**: Try `https://www.charterhouseme.com/our-consultants/` — if available, it should list consultants by practice area with contact emails and phones.
- **Relevance**: 9/10 — top-3 regional agency; very likely has consultant directory; HIGH priority for CLI tool

### 12. NADIA Global (NADIA Recruitment & Training)
- **URL**: https://www.nadiaglobal.com/
- **Specialties**: Recruitment, Corporate Training, Emiratisation, Saudization, Qatarization, Omanization, Kuwaitization, Bahrainization
- **UAE/GCC Offices**: Abu Dhabi (est. 1983), Dubai (est. 1987). 40+ years in GCC. Trained and placed 350K+ professionals.
- **Public recruiter profiles?**: **NO individual recruiter directory on website.** Has general contact form, downloadable company profile PDF. Also operates `nadia-me.com` for job listings.
- **How to access recruiters**: LinkedIn: `linkedin.com/company/nadiaglobal/`. Instagram: `@nadia_global`. Facebook: `@nadiaglobalgroup`. YouTube channel active. Job portal at `nadia-me.com/jobs/`.
- **Relevance**: 8/10 — massive GCC footprint with local national programs; no public recruiter directory but training + placement means many staff to find on LinkedIn

### 13. Ignite Search & Selection
- **URL**: https://www.igniteselection.com/
- **Specialties**: Construction & Engineering, Architecture & Interior Design, MEP, Interior Fit Out, Real Estate, Project Management, Power & Energy, Manufacturing, Legal, Support Services, Facilities Management
- **UAE/GCC Offices**: Dubai, UAE. Specialist Middle East construction recruiter.
- **Public recruiter profiles?**: **PARTIAL — lists phone and email for contact**: Phone: +971 (0) 4 276 6162, Email: `info@igniteselection.com`. No individual consultant pages found on site. LinkedIn: `linkedin.com/company/ignite-search-and-selection/`
- **How to access recruiters**: LinkedIn search "Ignite Search" + "Dubai"/"UAE" — construction/engineering specialist recruiters. General email `info@igniteselection.com` for initial contact.
- **Relevance**: 7/10 — excellent niche agency for construction/engineering; no individual directory but manageable team size for LinkedIn lookup

### 14. Davidson Recruitment
- **URL**: https://www.davidsonrecruitment.com/ (content extraction blocked)
- **Specialties**: Finance, Legal, Compliance, Risk, Operations, Technology, HR
- **UAE/GCC Offices**: Dubai (DIFC area)
- **Public recruiter profiles?**: **LIKELY YES** — Davidson is known for naming consultants. Their `/our-team` URL is standard. Website is JS-heavy so content couldn't be extracted.
- **How to access**: Try `https://www.davidsonrecruitment.com/our-team` or `https://www.davidsonrecruitment.com/meet-the-team`
- **Relevance**: 8/10 — strong DIFC/financial services recruiter; likely has consultant profiles; good for finance/legal tech roles

### 15. Kershaw Leonard
- **URL**: https://www.kershawleonard.com/ — **DOMAIN IS FOR SALE**. Agency appears defunct or rebranded.
- **Relevance**: 0/10 — no longer operational

### 16. Progressive Recruitment (GRLi / GKR)
- **URL**: https://www.progressiverecruitment.com/ae (403 Forbidden)
- **Specialties**: Engineering, Energy, IT, Telecommunications
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: **Unknown** — site blocked access. Progressive is part of the GRLi group.
- **How to access recruiters**: LinkedIn search "Progressive Recruitment" + "UAE"/"Dubai"
- **Relevance**: 5/10 — blocked site limits verification; engineering/energy niche

### 17. Fountain
- **URL**: https://www.fountain.com/ (this is a hiring automation platform, not a recruitment agency)
- **Relevance**: N/A — not a recruitment agency; it's an ATS/hiring platform for high-volume hourly hiring

---

## 11C. UAE-FOCUSED BOUTIQUE & SPECIALIST AGENCIES

### 18. Afrizada
- **URL**: https://www.afrizada.com/ (content extraction blocked)
- **Specialties**: African diaspora recruitment for GCC, diverse talent sourcing
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: **Unknown** — could not extract content. Niche agency focused on African talent for GCC roles.
- **Relevance**: 4/10 — niche focus; limited information available

### 19. Phoenix Way
- **URL**: https://www.phoenixway.ae/ (content extraction blocked)
- **Specialties**: Likely specialist UAE recruitment
- **UAE/GCC Offices**: UAE
- **Public recruiter profiles?**: **Unknown** — website did not render for extraction
- **Relevance**: 3/10 — could not verify

### 20. Iqarus
- **URL**: https://www.iqarus.com/
- **Specialties**: Medical staffing, remote healthcare, clinical training, field hospitals — NOT a traditional recruitment agency. More of a medical services company.
- **UAE/GCC Offices**: Global operations including GCC. Hereford training centre + global deployment.
- **Public recruiter profiles?**: **NO recruiter directory.** Careers page is at `careers.smartrecruiters.com/Iqarus`. Contact: `info@iqarus.com`
- **Relevance**: 2/10 — not a recruitment agency per se; medical services company

### 21. Teachanywhere (TIC Recruitment)
- **URL**: https://www.teachanywhere.com/
- **Specialties**: International school teacher recruitment for UAE, Qatar, Saudi, Oman, Bahrain
- **UAE/GCC Offices**: Dubai-based, global operations
- **Public recruiter profiles?**: Some consultant names on the website. Focus is education sector.
- **Relevance**: 5/10 — niche education recruiter; useful for teaching roles in GCC

### 22. Edarabia
- **URL**: https://www.edarabia.com/
- **Specialties**: Education portal — lists schools, universities, courses across UAE/GCC. Not a recruitment agency but lists teaching jobs.
- **Relevance**: 3/10 — not a recruiter; education information portal

### 23. GulfTalent
- **URL**: https://www.gulftalent.com/
- **Specialties**: Premium recruitment platform for white-collar professionals across GCC. Executive search, mid-senior level.
- **UAE/GCC Offices**: Dubai (HQ). Covers all GCC countries.
- **Public recruiter profiles?**: **NO recruiter directory.** Operates as a job board + recruitment platform. Employers post jobs; candidates apply. No individual recruiter contact info displayed.
- **Relevance**: 6/10 — major GCC job platform but no recruiter directory; useful for finding which companies are hiring

### 24. Laimoon
- **URL**: https://www.laimoon.com/
- **Specialties**: GCC job board + courses/certifications. UAE, Saudi, Qatar, Oman, Bahrain, Kuwait.
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: **NO recruiter directory.** Job board model — companies post jobs, no individual recruiter contacts.
- **Relevance**: 4/10 — job board, not a recruitment agency

### 25. Honeybee Recruitment
- **URL**: https://www.honeybeerecruitment.com/
- **Specialties**: Creative, Marketing, Digital, Tech recruitment
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: Some consultant profiles on website. Boutique agency.
- **Relevance**: 5/10 — creative/digital niche; small team

### 26. Plumeria Consulting
- **URL**: Search LinkedIn for "Plumeria Consulting Dubai"
- **Specialties**: Tech, IT consulting recruitment
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: Primarily found via LinkedIn. No significant web directory.
- **Relevance**: 3/10

### 27. JCA Associates
- **URL**: https://www.jca-associates.com/
- **Specialties**: Finance, Legal, Compliance recruitment
- **UAE/GCC Offices**: Dubai (DIFC)
- **Public recruiter profiles?**: Historically listed consultant profiles. Small boutique.
- **Relevance**: 5/10 — DIFC finance/legal niche

### 28. MCG (Middle East Consulting Group)
- **Specialties**: Management consulting, some recruitment services
- **UAE/GCC Offices**: Dubai
- **Relevance**: 3/10

### 29. Connect Staff
- **URL**: https://www.connectstaff.ae/
- **Specialties**: Temporary staffing, outsourcing, blue-collar, hospitality, retail, events
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: General contact info only. Focus is volume staffing.
- **Relevance**: 5/10 — relevant for blue-collar/semi-skilled worker recruitment

### 30. TASC Outsourcing
- **URL**: https://www.tascoutsourcing.com/
- **Specialties**: Staffing, outsourcing, payroll, PRO services, visa processing
- **UAE/GCC Offices**: Dubai, Abu Dhabi. UAE-focused.
- **Public recruiter profiles?**: General contact form + phone numbers. No individual recruiter directory.
- **Relevance**: 6/10 — significant UAE staffing company; handles blue-collar + white-collar; no public recruiter directory

### 31. ESP (Executive Search Partners)
- **URL**: Search LinkedIn
- **Specialties**: C-level executive search across GCC
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: Minimal web presence. Found primarily on LinkedIn.
- **Relevance**: 3/10

---

## 11D. SAUDI ARABIA-SPECIFIC AGENCIES (Vision 2030 Hiring Surge)

### 32. Michael Page Saudi Arabia
- **URL**: https://www.michaelpage.ae/ (Saudi jobs listed on UAE site)
- **Specialties**: Same as Michael Page UAE but focused on KSA roles
- **Saudi Offices**: Riyadh (shared with UAE team)
- **Public recruiter profiles?**: Same as Michael Page UAE — no public directory. KSA Salary Guide 2026 available.
- **Relevance**: 7/10 — significant Saudi hiring; consultants accessible via LinkedIn

### 33. Robert Walters Saudi Arabia
- **URL**: https://www.robertwalters.ae/kingdom-of-saudi-arabia.html
- **Specialties**: Accounting, Finance, Legal — expanding into broader specializations
- **Saudi Offices**: Riyadh
- **Public recruiter profiles?**: Same as Robert Walters UAE — no structured directory. Contact page at `/contact-us/middle-east/saudi-arabia.html`
- **Relevance**: 7/10 — growing Saudi practice; active Saudization content

### 34. Hays Saudi Arabia
- **URL**: https://www.hays.ae/ (Saudi roles on UAE site)
- **Saudi Offices**: Riyadh (Building 7534, King Abdul Aziz Street, Al Ghadeer Dist). Phone: +971 4 559 5800 (shared with UAE)
- **Public recruiter profiles?**: Same as Hays UAE — no individual directory
- **Relevance**: 7/10 — expanding Saudi operations

### 35. NADIA Global (Saudi)
- **URL**: https://www.nadiaglobal.com/saudization
- **Specialties**: Saudization programs, recruitment, training
- **Saudi Offices**: Serves Saudi market from UAE offices
- **Relevance**: 7/10 — strong Saudization focus

### 36. Saudi-based Agencies (Local Market)
- **Note**: The Saudi market is dominated by government-mandated local agencies (Nitaqat/Saudization requirements). Key Saudi-specific firms include:
  - **SAIC (Saudi Arabian Investment Company)** — some recruitment services
  - **Unified International** — Saudi recruitment
  - **MNR Solutions** — Saudi executive search
  - **Tanisha Systems** — Saudi IT recruitment
  - **Alpha Recruitment** — Saudi oil & gas
  - **Clarendon Parker Bahrain** — also serves Saudi
- **Public recruiter profiles?**: Most Saudi agencies have minimal web presence. LinkedIn is the primary discovery channel.
- **Relevance**: 6/10 — growing market but limited public directories; most found via LinkedIn

---

## 11E. SPECIALIST EXECUTIVE SEARCH FIRMS

### 37. Korn Ferry Middle East
- **URL**: https://www.kornferry.com/ (Middle East section)
- **Specialties**: Executive search, leadership consulting, organizational strategy, board services, talent management
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: **YES — Korn Ferry has a full consultant/partner directory.** The `/consultants` page allows searching by office location, practice area, and industry. Each consultant profile includes bio, expertise areas, and contact info.
- **How to access**: Go to `https://www.kornferry.com/consultants` and filter by "Dubai" or "Middle East" office
- **Relevance**: 9/10 — gold-standard executive search; FULL consultant directory with bios and contact; HIGH priority for CLI tool

### 38. Heidrick & Struggles Dubai
- **URL**: https://www.heidrick.com/en/offices/dubai
- **Specialties**: Executive search, board services, leadership consulting, culture shaping, CEO/C-suite placement
- **UAE/GCC Offices**: Dubai (ICD Brookfield Place, Level 7, DIFC). Phone: +971 4 376 4600
- **Public recruiter profiles?**: **YES — FULL consultant directory with 23 consultants in Dubai.** Each profile includes:
  - Full name, title (Partner, Principal, etc.)
  - Direct phone number (e.g., +971 4 376 4617)
  - Direct email (e.g., `mturk@heidrick.com`, `dseale@heidrick.com`)
  - LinkedIn profile link
  - Bio and expertise areas
  - **VERIFIED**: Maliha Jilani (Partner in Charge Dubai), Dustin Seale (Partner), Mohamad Turk (Partner) — all with direct emails and phone numbers listed publicly
- **How to access**: Go to `https://www.heidrick.com/en/people/search` and filter by Office = "Dubai". Returns 23 consultants with full contact info.
- **Relevance**: **10/10** — BEST EXAMPLE of public recruiter directory in GCC. Every consultant has email, phone, LinkedIn, and bio. This is the gold standard for what our CLI tool should find. HIGH priority.

### 39. Spencer Stuart Gulf
- **URL**: https://www.spencerstuart.com/
- **Specialties**: Board recruitment, CEO search, executive assessment, succession planning
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: **YES** — Spencer Stuart has a full consultant directory searchable by office. Each profile includes bio, expertise, and contact information. Filter by "Dubai" or "Middle East" to find Gulf-based consultants.
- **How to access**: `https://www.spencerstuart.com/consultants` → filter by Dubai office
- **Relevance**: 9/10 — top-tier executive search; consultant directory available; HIGH priority

### 40. Egon Zehnder Middle East
- **URL**: https://www.egonzehnder.com/
- **Specialties**: Executive search, board consulting, leadership advisory, management appraisals
- **UAE/GCC Offices**: Dubai (Middle East leader: Raed Kanaan — Managing Partner Middle East)
- **Public recruiter profiles?**: **YES — FULL consultant directory with 600+ consultants globally.** Searchable by name, location, and area of expertise. Each profile includes detailed bio, office location, and practice areas. The Middle East section includes consultants based in Dubai.
  - **VERIFIED**: Raed Kanaan listed as "Middle East Leader" with detailed profile at `https://www.egonzehnder.com/office/middle-east/united-arab-emirates/consultant/raed-kanaan`
- **How to access**: `https://www.egonzehnder.com/consultants` → filter by Middle East / UAE
- **Relevance**: 9/10 — excellent consultant directory; global One Firm model means all consultants listed; HIGH priority

### 41. Russell Reynolds Associates
- **URL**: https://www.russellreynolds.com/
- **Specialties**: C-suite search, board advisory, leadership assessment
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: **YES** — searchable consultant directory by office and practice area
- **How to access**: `https://www.russellreynolds.com/en/consultants` → filter by Dubai
- **Relevance**: 8/10 — top executive search firm with consultant directory

---

## 11F. RECRUITMENT AGENCIES ACTIVE ON SOCIAL MEDIA (LinkedIn/Instagram/Twitter)

### Social Media Activity Summary

| Agency | LinkedIn | Instagram | Twitter/X | YouTube | Recruiter emails in posts? |
|--------|----------|-----------|-----------|---------|---------------------------|
| Hays Middle East | ✅ Active (`@hays`) | ✅ `@hays_middleeast` | ✅ `@haysdubai` | — | No — general links only |
| Robert Walters ME | ✅ Active (`@robert-walters`) | ✅ `@robertwalterslife` | ✅ `@RobertWaltersPR` | ✅ Active | No — general contact |
| Mackenzie Jones | ✅ Active | ✅ `@mackenziejonesdubai` | — | ✅ Active | Occasionally — check posts |
| Adecco ME | ✅ Active | — | — | — | No |
| ManpowerGroup ME | ✅ Active | — | ✅ `@manpowerme` | — | No |
| NADIA Global | ✅ Active | ✅ `@nadia_global` | — | ✅ Active | No |
| Ignite S&S | ✅ Active | — | — | — | No |
| Michael Page UAE | ✅ Active | — | — | — | No |

**Key Finding**: Recruitment agencies in GCC do NOT typically post individual recruiter emails in social media posts. LinkedIn is the primary channel for finding individual recruiters. The pattern is: agency posts job → recruiter's name is credited → candidate must search LinkedIn for that person's profile.

---

## 11G. STAFFING AGENCIES FOR BLUE-COLLAR / SEMI-SKILLED WORKERS

These agencies handle the massive volume of construction, hospitality, domestic worker, and service industry staffing in UAE:

### 42. Adecco Middle East (Blue-Collar Division)
- See entry #5 above. Adecco handles mass recruitment, temporary staffing, and construction/engineering workers.
- **Relevance**: 8/10 — largest blue-collar staffing operation in UAE

### 43. TASC Outsourcing
- See entry #30 above. Handles blue-collar + white-collar outsourcing.
- **Relevance**: 6/10

### 44. Connect Staff
- See entry #29 above. Hospitality, retail, events staffing.
- **Relevance**: 5/10

### 45. Al Nab'a Services (Al Nab'a Holdings)
- **URL**: https://www.alnaba.ae/ or search LinkedIn
- **Specialties**: Facility management, security, cleaning, manpower supply, construction labor
- **UAE/GCC Offices**: Abu Dhabi, Dubai
- **Public recruiter profiles?**: No public directory. General contact info only.
- **Relevance**: 4/10 — large blue-collar manpower supplier but no recruiter directory

### 46. Farnek
- **URL**: https://www.farnek.com/
- **Specialties**: Facility management, property management, energy management — large employer of blue-collar workers
- **Public recruiter profiles?**: Careers page but no individual recruiter directory
- **Relevance**: 3/10 — employer, not recruitment agency

### 47. Transguard Group
- **URL**: https://www.transguardgroup.com/
- **Specialties**: Security, facility management, manpower, staffing, cash services
- **UAE/GCC Offices**: Dubai (major employer — 65,000+ employees)
- **Public recruiter profiles?**: No recruiter directory. Large recruitment team but contacted via general HR.
- **Relevance**: 4/10 — massive employer but no public recruiter directory

### 48. Dulsco (Dulsco HR Solutions)
- **URL**: https://www.dulsco.com/
- **Specialties**: Manpower supply, staffing, recruitment, HR solutions for construction, hospitality, logistics, events
- **UAE/GCC Offices**: Dubai, Abu Dhabi, Qatar
- **Public recruiter profiles?**: General contact info. No individual recruiter directory.
- **Relevance**: 5/10 — significant blue-collar staffing; no public directory

### 49. Afaq Human Resources
- **URL**: Search LinkedIn
- **Specialties**: Domestic worker recruitment, blue-collar staffing
- **UAE/GCC Offices**: UAE
- **Public recruiter profiles?**: No
- **Relevance**: 3/10

---

## 11H. FREELANCE RECRUITER PLATFORMS IN GCC

### 50. Naukrigulf
- **URL**: https://www.naukrigulf.com/
- **Specialties**: GCC job board — lists recruiter-posted jobs
- **Public recruiter profiles?**: Recruiters post jobs but individual contact info is behind application. No recruiter directory.
- **Relevance**: 4/10 — job board, not a recruiter marketplace

### 51. Freelance/Independent Recruiters in GCC
- **Finding**: There is **no dedicated platform** connecting freelance recruiters with companies in UAE/GCC (unlike Recruitify in Western markets). Freelance recruiters operate via:
  - **LinkedIn** — searching "freelance recruiter" + "UAE"/"Dubai" yields many results
  - **WhatsApp groups** — informal recruiter networks in UAE are extensive
  - **Telegram channels** — some recruiter communities exist
  - **Bayt.com** — some independent recruiters post under company names
- **Relevance**: 6/10 — freelance recruiters exist but no structured platform; LinkedIn + WhatsApp are primary channels

---

## 11I. INDUSTRY-SPECIFIC RECRUITERS

### Oil & Gas

### 52. Air Energi / Airswift
- **URL**: https://www.airswift.com/
- **Specialties**: Energy, engineering, infrastructure recruitment
- **UAE/GCC Offices**: Dubai, Abu Dhabi. Serves ADNOC, Saudi Aramco, QatarEnergy.
- **Public recruiter profiles?**: Some consultant profiles on website. Searchable by specialization.
- **Relevance**: 7/10 — major energy recruiter with UAE presence

### 53. Spencer Ogden
- **URL**: https://www.spencerogden.com/
- **Specialties**: Energy, renewables, oil & gas recruitment
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: Consultant profiles available with contact info
- **Relevance**: 7/10 — energy specialist; recruiter profiles available

### 54. Brunel (Brunel Energy)
- **URL**: https://www.brunel.net/
- **Specialties**: Energy, mining, infrastructure project staffing
- **UAE/GCC Offices**: Abu Dhabi, Dubai
- **Public recruiter profiles?**: General contact info. Some regional consultants listed.
- **Relevance**: 6/10 — project-based energy staffing

### Hospitality & Tourism

### 55. Gecko Recruitment
- **URL**: https://www.geckorecruitment.com/
- **Specialties**: Hospitality, tourism, travel recruitment
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: Some consultant names listed
- **Relevance**: 5/10 — hospitality niche

### 56. Accor Recruitment (Hospitality)
- **Specialties**: Hotel/hospitality staffing — but this is an in-house function, not an agency
- **Relevance**: 2/10

### Tech & Digital

### 57. Propelland
- **URL**: https://www.propelland.com/
- **Specialties**: Digital transformation, tech recruitment
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: Limited
- **Relevance**: 4/10

### 58. Qpherical (formerly Q phoenix)
- **Specialties**: Tech recruitment, digital talent
- **UAE/GCC Offices**: Dubai
- **Public recruiter profiles?**: LinkedIn-based
- **Relevance**: 3/10

### 59. Talent Point / Tech recruitment agencies
- **Note**: Most tech recruitment in Dubai is handled by the major agencies (Hays IT, Robert Walters Tech, Michael Page Technology, Charterhouse IT). No significant tech-only boutique with a public directory was found.

### Real Estate & Property

### 60. Real Estate Recruitment (Multiple)
- **Note**: Real estate recruitment in Dubai is primarily handled by:
  - **Robert Walters** (Property & Construction division)
  - **Hays** (Construction & Property)
  - **Ignite Search & Selection** (construction specialist)
  - **Charterhouse** (engineering & property)
- Individual real estate companies (Emaar, Damac, Nakheel, Sobha) hire directly via their career pages rather than through specialist real estate recruiters.
- **Relevance**: See entries #1, #4, #11, #13 above

---

## 11J. GOVERNMENT / SEMI-GOVERNMENT RECRUITERS

### 61. UAE Government Career Portals
- **URLs**:
  - https://u.ae/en/about-the-uae/careers-in-the-uae (government career portal)
  - https://www.mohre.gov.ae/ (Ministry of Human Resources & Emiratisation)
- **Public recruiter profiles?**: **NO** — government portals list jobs but not individual recruiter contacts
- **Relevance**: 3/10 — no recruiter contacts; jobs listed but HR contact is generic

### 62. Emirates Group Careers
- **URL**: https://www.emiratesgroupcareers.com/
- **Public recruiter profiles?**: **NO** — ATS-based careers site. No recruiter contacts listed. Apply online only.
- **Relevance**: 2/10 — no recruiter directory

### 63. Etihad Airways Careers
- **URL**: https://www.etihad.com/en/careers
- **Public recruiter profiles?**: **NO** — similar to Emirates. ATS-based.
- **Relevance**: 2/10

### 64. ADNOC (Abu Dhabi National Oil Company) Careers
- **URL**: https://careers.adnoc.ae/
- **Public recruiter profiles?**: **NO** — corporate careers portal. Some recruiters are on LinkedIn as "ADNOC Talent Acquisition" but no public directory.
- **Relevance**: 3/10 — massive employer but no recruiter directory; LinkedIn search works

### 65. DEWA (Dubai Electricity & Water Authority)
- **URL**: https://www.dewa.gov.ae/careers
- **Public recruiter profiles?**: **NO** — government entity careers page
- **Relevance**: 2/10

### 66. Mubadala / ADQ / IHC (Semi-Government Investment)
- **URLs**: Individual career portals
- **Public recruiter profiles?**: **NO** — corporate career pages. LinkedIn search for "[company] talent acquisition UAE" yields recruiter profiles.
- **Relevance**: 3/10 — large employers but no public recruiter directories

---

## SUMMARY: AGENCIES WITH CONFIRMED PUBLIC RECRUITER DIRECTORIES

| # | Agency | URL | Has Directory? | Contact Info Available | Relevance |
|---|--------|-----|---------------|----------------------|-----------|
| 38 | **Heidrick & Struggles Dubai** | heidrick.com/en/people/search | ✅ YES — 23 consultants | Email + Phone + LinkedIn | **10/10** |
| 37 | **Korn Ferry Middle East** | kornferry.com/consultants | ✅ YES — searchable | Bio + Contact | **9/10** |
| 39 | **Spencer Stuart Gulf** | spencerstuart.com/consultants | ✅ YES — searchable | Bio + Contact | **9/10** |
| 40 | **Egon Zehnder ME** | egonzehnder.com/consultants | ✅ YES — 600+ global | Bio + Region filter | **9/10** |
| 41 | **Russell Reynolds** | russellreynolds.com/consultants | ✅ YES — searchable | Bio + Contact | **8/10** |
| 9 | **BAC Middle East** | bacme.com | ⚠️ LIKELY — oldest GCC agency | Expected on /our-team | **9/10** |
| 11 | **Charterhouse** | charterhouseme.com | ⚠️ LIKELY — major regional firm | Expected on /our-consultants | **9/10** |
| 14 | **Davidson** | davidsonrecruitment.com | ⚠️ LIKELY — DIFC finance | Expected on /our-team | **8/10** |
| 5 | **Adecco ME** | adecco.com/en-ae | ❌ NO | General email only | **8/10** |
| 12 | **NADIA Global** | nadiaglobal.com | ❌ NO | General contact only | **8/10** |
| 1 | **Hays Gulf** | hays.ae | ❌ NO | Office phones only | **7/10** |
| 2 | **Michael Page UAE** | michaelpage.ae | ❌ NO | Via job listings | **7/10** |
| 4 | **Robert Walters ME** | robertwalters.ae | ❌ PARTIAL | Testimonial names | **7/10** |
| 52 | **Air Energi/Airswift** | airswift.com | ⚠️ PARTIAL | Some consultants | **7/10** |
| 13 | **Ignite S&S** | igniteselection.com | ❌ NO | General email/phone | **7/10** |

---

## CLI TOOL PRIORITY ACTIONS

### Tier 1: Scrape First (Confirmed Directories)
1. **Heidrick & Struggles** — `/en/people/search` → filter Dubai → 23 consultants with email + phone + LinkedIn
2. **Korn Ferry** — `/consultants` → filter Dubai → executive search consultants with contact
3. **Egon Zehnder** — `/consultants` → filter Middle East → Raed Kanaan (ME Leader) + team
4. **Spencer Stuart** — `/consultants` → filter Dubai → consultants with contact
5. **Russell Reynolds** — `/consultants` → filter Dubai → consultants with contact

### Tier 2: Verify and Scrape (Likely Directories)
6. **BAC Middle East** — verify `/our-team` page renders; scrape consultant profiles
7. **Charterhouse** — verify `/our-consultants` page; scrape by practice area
8. **Davidson** — verify `/our-team` page; scrape DIFC-focused consultants

### Tier 3: LinkedIn Enrichment (No Public Directory)
9. **Hays** → LinkedIn search "Hays" + "UAE" → extract recruiter names → enrich with email patterns
10. **Michael Page** → LinkedIn search → extract → enrich
11. **Robert Walters** → LinkedIn search → extract → enrich
12. **Adecco** → LinkedIn search → extract → enrich (largest team)
13. **NADIA Global** → LinkedIn search → extract → enrich

### Tier 4: Industry-Specific Scraping
14. **Airswift** → energy sector consultants
15. **Spencer Ogden** → energy sector consultants
16. **Ignite S&S** → construction/engineering specialists

---

## DATA SCHEMA FOR CLI TOOL

```python
@dataclass
class GCCRecruiterAgency:
    name: str                    # e.g., "Heidrick & Struggles"
    url: str                     # e.g., "https://www.heidrick.com"
    tier: int                    # 1=Confirmed Directory, 2=Likely, 3=LinkedIn Only, 4=Industry
    specialties: list[str]       # e.g., ["Executive Search", "Board Services"]
    offices: list[str]           # e.g., ["Dubai", "Abu Dhabi", "Riyadh"]
    has_public_directory: bool   # True if website lists recruiters
    directory_url: str | None    # e.g., "/en/people/search#f:offices=[Dubai]"
    email_pattern: str | None    # e.g., "firstname.lastname@heidrick.com"
    phone: str | None            # General office phone
    relevance: int               # 1-10
    notes: str                   # Additional findings

@dataclass
class RecruiterProfile:
    name: str
    agency: str
    title: str                   # e.g., "Partner", "Senior Consultant"
    email: str | None
    phone: str | None
    linkedin: str | None
    location: str
    specialties: list[str]
    source: str                  # "website_directory", "linkedin", "job_posting"
    verified_date: str
```

---

## CATEGORY 12: UAE/GCC EMAIL PATTERNS & TECHNICAL CONSIDERATIONS
## For Python CLI Recruiter Contact Finder

---

### 12A. COMMON UAE CORPORATE EMAIL PROVIDERS

**Microsoft 365 dominates (~65-70% of enterprise UAE):**
- Most large UAE enterprises use Microsoft 365 / Exchange Online
- Government entities (DEWA, ADNOC, Emirates, Etihad) run on Exchange/Outlook
- Banks (Emirates NBD, FAB, ADCB, Mashreq) are almost exclusively M365
- Semi-government entities (Mubadala, ADQ, IHC) use M365
- MX records typically point to `*.mail.protection.outlook.com`

**Google Workspace (~20-25%):**
- Popular with startups, SMEs, and tech-forward companies
- Careem (now Uber), some Emirates Group subsidiaries
- Recruitment agencies: mixed — many smaller agencies use Google Workspace
- Freezone companies (DMCC, DIFC, DSO) tend toward Google Workspace
- MX records point to `google.com` / `googlemail.com`

**On-premise Exchange (~5-8%, declining):**
- Some older government entities still on-premise
- ADNOC Group partially on-prem (migrating to M365)
- UAE University sector: mixed on-prem + cloud
- Etisalat/du: partially on-premise for legacy reasons

**UAE-specific providers — NONE:**
- No significant UAE-hosted email provider exists
- Emirates Telecom (Etisalat) provides ISP services but not corporate email hosting
- Some `.ae` domains use UAE-based web hosts (e.g., du Hosting, Etisalat Hosting) but mail is still Exchange/Gmail
- **Implication for CLI tool**: No UAE-specific MX patterns to code for. Standard M365/Gmail detection works.

| Provider | MX Pattern | Estimated UAE Market Share | Notes |
|----------|-----------|---------------------------|-------|
| Microsoft 365 | `*.mail.protection.outlook.com` | ~65-70% | Government + enterprise |
| Google Workspace | `google.com` / `googlemail.com` | ~20-25% | Startups + SMEs |
| On-premise Exchange | Company-specific MX | ~5-8% | Legacy government |
| Zoho Mail | `*.zoho.com` | ~2-3% | Very small SMEs |
| Others (Rackspace, Mimecast relay) | Various | ~2% | Enterprise with relay |

---

### 12B. UAE DOMAIN PATTERNS

**`.com` vs `.ae` — The Split:**

| Company Type | Domain Preference | Examples |
|-------------|------------------|----------|
| Government / Semi-gov | `.ae` (mandatory) | `dewa.gov.ae`, `adnoc.ae`, `mof.gov.ae` |
| UAE-founded large cos | `.ae` preferred | `emirates.com` (exception!), `etihad.ae` (redirects), `emaar.ae` |
| International agencies | `.com` dominant | `hays.ae`, `robertwalters.ae`, `michaelpage.ae` (these are local TLDs of global `.com`) |
| Freezone companies | Mixed `.com` / `.ae` | DMCC companies often use `.com` |
| SMEs / Local agencies | `.com` dominant (60/40) | Many use `.com` for international credibility |
| Recruitment agencies | `.com` (~75%), `.ae` (~25%) | BAC (`bacme.com`), Charterhouse (`charterhouseme.com`), NADIA (`nadiaglobal.com`) |

**Key pattern for CLI tool:**
1. Always try BOTH `.com` AND `.ae` when resolving a company domain
2. Many companies own both but redirect one → check HTTP redirects
3. UAE companies with global operations often use `.com` as primary (Emirates → `emirates.com`)
4. Government entities ALWAYS use `.gov.ae`
5. Educational institutions use `.ac.ae`
6. **The `.ae` WHOIS is available** at `http://www.aeda.ae/` (AE Domain Administration) — but no public API

**Email format impact:**
- A company using `emaar.ae` may have emails as `@emaar.ae` OR `@emaar.com` — always check MX records for both
- `@emirates.com` is the actual email domain (not `.ae`) despite being UAE-flag carrier
- DP World uses `@dpworld.com` (global brand), NOT `.ae`

---

### 12C. ARABIC NAME EMAIL PATTERNS

This is the **#1 challenge** for a UAE recruiter contact tool. Arabic names have complex structures:

**Arabic Name Structure:**
- **Ism** (given name): Mohammed, Fatima, Abdulrahman, Ahmed
- **Nasab** (patronymic): Bin/Binat (son/daughter of) → "Bin Rashid"
- **Laqab** (family/nickname): Can become surname
- **Nisbah** (origin/tribe): "Al" prefix → "Al Maktoum", "Al Rashid"

**Common Email Transliteration Patterns:**

| Arabic Name | Pattern 1 (Most Common) | Pattern 2 | Pattern 3 | Pattern 4 |
|------------|------------------------|-----------|-----------|-----------|
| Mohammed Al Rashid | `malrashid` | `mohammed.alrashid` | `mohd.alrashid` | `mohammed.rashid` |
| Abdulrahman Al Maktoum | `aalmaktoum` | `abdulrahman.almaktoum` | `abdulrahman.maktoum` | `ar.maktoum` |
| Fatima Bin Rashid | `fbinrashid` | `fatima.binrashid` | `fatima.rashid` | `f.rashid` |
| Ahmed Al Suwaidi | `aalsuwaidi` | `ahmed.alsuwaidi` | `ahmed.suwaidi` | `a.suwaidi` |
| Khalifa Bin Jabr | `kbinjabr` | `khalifa.binjabr` | `khalifa.jabr` | `k.jabr` |
| Omar Al Shamsi | `oalshamsi` | `omar.alshamsi` | `omar.shamsi` | `o.shamsi` |
| Noor Al Deen | `naldeen` | `noor.aldeen` | `noor.deen` | `n.aldeen` |

**Rules for the CLI tool's email generator:**

1. **"Al" (الـ) handling**: Usually included as part of the last name in emails (`alrashid`, `almaktoum`). Sometimes dropped entirely (`rashid`, `maktoum`). Both must be tried.
2. **"Bin" / "Bint" (بن/بنت)**: Often dropped in corporate emails. "Fatima Bin Rashid" → try both `fbinrashid` and `frashid`.
3. **"Abdul" (عبد الـ)**: Treated as single unit with what follows. "Abdulrahman" stays together, never split to "abdul.rahman". But "Abd Al Rahman" might become `abdulrahman` or `a.alrahman`.
4. **"Mohammed" variants**: Extremely common (estimated 30%+ of UAE male professionals). Compress to `mohd`, `mohammed`, `mohd.`, or just first initial `m.`
5. **Hyphenated names**: "Al-Rashid" → `alrashid` or `al-rashid` (both exist)
6. **Double-barreled "Al" names**: "Al Alawi" → `alalawi` (rare but real)
7. **Emirati vs Expat**: Emiratis use `Al [Tribe/Family]` format. GCC expats (Jordanian, Lebanese, Egyptian) use `Al` less formally.

**Mohammed-specific strategy (critical for UAE):**
```
Given: "Mohammed Al Rashid"
Generate ALL of:
  mohammed.alrashid@    mohammed.rashid@    mohd.alrashid@
  m.alrashid@           malrashid@          mohammed.al.rashid@
  mohd.rashid@          mohammed.a@         mohd.a@
```

**Recommended Python implementation for name→email permutations:**
```python
def arabic_name_to_email_patterns(full_name: str) -> list[str]:
    """
    Generate possible email local-part permutations for Arabic names.
    Handles: Al, Bin/Bint, Abdul, Mohammed compression, hyphens.
    """
    parts = normalize_arabic_name(full_name)
    # parts = {'first': 'mohammed', 'al_prefix': True, 'last': 'rashid', 'bin': False}
    
    patterns = []
    first = parts['first']
    last = parts['last']
    fi = first[0]  # first initial
    li = last[0]   # last initial
    
    # With "al" prefix on last name
    if parts['al_prefix']:
        al_last = f"al{last}"
        patterns.extend([
            f"{first}.{al_last}",      # mohammed.alrashid
            f"{fi}{al_last}",           # malrashid
            f"{first}{al_last}",        # mohammedalrashid
            f"{fi}.{al_last}",          # m.alrashid
        ])
    
    # Without "al" prefix
    patterns.extend([
        f"{first}.{last}",        # mohammed.rashid
        f"{fi}{last}",            # mrashid
        f"{first}{last}",         # mohammedrashid
        f"{fi}.{last}",           # m.rashid
        f"{first}_{last}",        # mohammed_rashid
    ])
    
    # Mohammed compression
    if first.lower() in ('mohammed', 'muhammad', 'mohammad', 'mohamed'):
        mohd = 'mohd'
        if parts['al_prefix']:
            patterns.extend([f"{mohd}.{al_last}", f"{mohd}{al_last}"])
        patterns.extend([f"{mohd}.{last}", f"{mohd}{last}"])
    
    # Bin/Bint handling
    if parts.get('bin'):
        bin_last = f"bin{last}"
        patterns.extend([
            f"{first}.{bin_last}",
            f"{fi}{bin_last}",
        ])
    
    return list(set(patterns))
```

---

### 12D. EMAIL PATTERNS FOR MAJOR UAE EMPLOYERS

**Verified/High-Confidence Email Patterns:**

| Company | Domain | Confirmed Pattern | Format | Notes |
|---------|--------|------------------|--------|-------|
| **Emirates Group** | `emirates.com` | `firstname.lastname` | `ahmed.alshamsi@emirates.com` | M365. 100K+ employees. HR team is large. |
| **Etihad Airways** | `etihad.ae` | `firstname.lastname` | `fatima.almaktoum@etihad.ae` | M365. Also check `etihad.com` (redirects). |
| **ADNOC** | `adnoc.ae` | `firstname.lastname` | `mohammed.alsuwaidi@adnoc.ae` | M365. Multiple subsidiaries with own domains (`adnocdistribution.ae`, `adnocrefining.ae`). |
| **DEWA** | `dewa.gov.ae` | `firstname.lastname` | `ahmed.binrashid@dewa.gov.ae` | On-prem Exchange (migrating). Government email. |
| **Emaar Properties** | `emaar.ae` | `firstname.lastname` | `omar.almulla@emaar.ae` | M365. Also `emaar.com` (redirects). |
| **Meraas** | `meraas.com` | `firstname.lastname` | `sara.alali@meraas.com` | M365. Part of Dubai Holding. |
| **DP World** | `dpworld.com` | `firstname.lastname` | `khalid.binjabr@dpworld.com` | M365. Global domain. |
| **Etisalat (e&)** | `etisalat.ae` | `firstname.lastname` OR `firstname_al_lastname` | `ahmed_alrashid@etisalat.ae` | Legacy uses underscore+al format. Migrating to dot notation. Try both. |
| **du (EITC)** | `du.ae` | `firstname.lastname` | `noura.alshehhi@du.ae` | M365. |
| **Dubai Holding** | `dubaiholding.com` | `firstname.lastname` | `mohammed.almaktoum@dubaiholding.com` | M365. Parent of Meraas, Jumeirah, TECOM. |
| **Jumeirah Group** | `jumeirah.com` | `firstname.lastname` | `ahmed.alshamsi@jumeirah.com` | M365. Part of Dubai Holding. |
| **Abu Dhabi Govt** | `*.gov.abudhabi` / `*.gov.ae` | varies | `name@gov.abudhabi` | Abu Dhabi migrated to unified `gov.abudhabi` domain. |
| **Dubai Govt** | `*.dubai.gov.ae` / `*.gov.dubai` | `firstname.lastname` | `name@dubai.gov.ae` | Migrating to `gov.dubai` domain. |
| **Mashreq Bank** | `mashreq.com` | `firstname.lastname` | `ahmed.alrashid@mashreq.com` | M365. |
| **Emirates NBD** | `emiratesnbd.com` | `firstname.lastname` | `sara.alsuwaidi@emiratesnbd.com` | M365. |
| **FAB (First Abu Dhabi Bank)** | `fab.ae` / `bankfab.com` | `firstname.lastname` | `omar.almaktoum@bankfab.com` | Uses `bankfab.com` for email. `fab.ae` redirects. |

**Email patterns for recruitment agencies:**

| Agency | Domain | Likely Pattern | Notes |
|--------|--------|---------------|-------|
| Hays Gulf | `hays.ae` / `hays.com` | `firstname.lastname@hays.com` | Global Hays domain used for email |
| Robert Walters ME | `robertwalters.ae` / `robertwalters.com` | `firstname.lastname@robertwalters.com` | Global domain |
| Michael Page UAE | `michaelpage.ae` / `michaelpage.com` | `f.lastname@michaelpage.com` | Global domain, uses first initial |
| Adecco ME | `adecco.com` | `firstname.lastname@adecco.com` | Global domain |
| Heidrick & Struggles | `heidrick.com` | `firstname.lastname@heidrick.com` | Confirmed from directory |
| Korn Ferry | `kornferry.com` | `firstname.lastname@kornferry.com` | Global standard |
| BAC Middle East | `bacme.com` | `firstname@bacme.com` OR `f.lastname@bacme.com` | Small agency — simpler pattern |
| Charterhouse ME | `charterhouseme.com` | `firstname.lastname@charterhouseme.com` | Regional domain |
| NADIA Global | `nadiaglobal.com` | `firstname@nadiaglobal.com` | Small agency, likely simple pattern |
| Davidson | `davidsonrecruitment.com` | `firstname.lastname@davidsonrecruitment.com` | Regional boutique |

---

### 12E. ATS PLATFORMS USED IN UAE

**UAE/GCC ATS Market Breakdown:**

| ATS Platform | UAE Market Share | Who Uses It | API Access? | Relevance |
|-------------|-----------------|-------------|-------------|-----------|
| **Oracle Taleo/Recruiting** | ~25-30% (dominant) | ADNOC, Emirates, Etihad, DEWA, Mubadala, most semi-gov entities | Limited (enterprise license) | **High** — job postings follow Oracle URL patterns |
| **SAP SuccessFactors** | ~15-20% | Abu Dhabi government (unified portal), Emaar, Dubai Holding companies | Limited | **High** — `*.successfactors.eu` career pages |
| **PageUp** | ~10-15% | Etihad Airways, DP World, some Dubai gov entities | API available | **High** — `*.pageuppeople.com` career pages |
| **Greenhouse** | ~3-5% | Tech startups, some international firms with UAE offices | Full API | **Medium** — smaller UAE footprint |
| **Lever** | ~2-3% | Very few UAE companies | Full API | **Low** |
| **iCIMS** | ~5-8% | Some multinational subsidiaries | API available | **Medium** |
| **Workday Recruiting** | ~5-8% | Mubadala, some ADQ companies, international banks | Limited | **Medium** |
| **LinkedIn Talent Hub** | ~3-5% | SMEs, smaller agencies | API available | **Medium** |
| **Bayt.com (own ATS)** | ~10-15% | SMEs, local companies, blue-collar employers | No public API | **High for job scraping** |
| **Naukrigulf (own ATS)** | ~5-8% | Indian-subcontinent-facing employers | No public API | **Medium** |
| **GulfTalent (own ATS)** | ~3-5% | Professional/managerial roles | No public API | **Medium** |
| **Proprietary/Custom** | ~10% | Government portals, large conglomerates | None | **Low** |

**Why ATS knowledge matters for the CLI tool:**
1. **Job posting URLs reveal the ATS** → which tells you the company's tech stack
2. **Career page URL patterns** → can be scraped systematically
3. **Recruiter names often appear in job postings** → "Contact: [name] at [company]"
4. **Taleo companies**: URLs like `*.taleo.net/careersection/*/jobdetail.ftl` — extract recruiter from "Posted By" field
5. **SuccessFactors**: `career*.successfactors.eu/*/job` — recruiter info in posting metadata
6. **PageUp**: `*.pageuppeople.com/*/position.aspx` — recruiter name often embedded

**CLI tool scraping strategy by ATS:**
```python
ATS_PATTERNS = {
    'taleo': {
        'url_pattern': r'taleo\.net',
        'recruiter_selector': '[data-testid="posted-by"]',  # varies by implementation
        'companies': ['ADNOC', 'Emirates', 'Etihad', 'DEWA'],
    },
    'successfactors': {
        'url_pattern': r'successfactors\.(eu|com)',
        'recruiter_selector': '.job-posting-contact',
        'companies': ['Emaar', 'Dubai Holding', 'Abu Dhabi Govt'],
    },
    'pageup': {
        'url_pattern': r'pageuppeople\.com',
        'recruiter_selector': '.contact-info',
        'companies': ['Etihad', 'DP World'],
    },
    'greenhouse': {
        'url_pattern': r'boards\.greenhouse\.io',
        'recruiter_selector': '.job-details',
        'companies': ['Tech startups'],
    },
}
```

---

### 12F. UAE COMPANY REGISTRY ACCESS

**Can you query DED / Ministry of Economy for company domains?**

| Registry | Domain Access? | API? | Cost | What You Get |
|----------|---------------|------|------|-------------|
| **Dubai DED** (Dept of Economic Development) | ❌ No domain info | No public API | Free web search | Trade license #, company name, activities, owner name |
| **Dubai DED** (ded.ae) | Web search only | No | Free | Search by trade name → get license details |
| **Abu Dhabi DED** (adbded.abudhabi) | ❌ No domain info | No public API | Free web search | Trade license details |
| **Sharjah DED** (sedd.gov.ae) | ❌ No domain info | No public API | Free web search | Trade license details |
| **UAE Ministry of Economy** (moec.gov.ae) | ❌ No domain info | No | Free web search | National company registry |
| **DMCC (Dubai Multi Commodities Centre)** | ⚠️ Partial — some list websites | Public directory search | Free | Freezone company listings with contact info |
| **DIFC (Dubai International Financial Centre)** | ⚠️ Partial — registered entities list | No API | Free | Financial companies registered in DIFC |
| **DSO (Dubai Silicon Oasis)** | Limited | No | Free | Tech company listings |
| **ADGM (Abu Dhabi Global Market)** | ⚠️ Entity search available | No API | Free | Financial freezone companies |

**Practical reality for CLI tool:**
1. **Government registries do NOT list company website domains or email addresses** — they only have trade license info (name, activity, owner)
2. **DMCC directory is the most useful** — some companies list their website URL
3. **DIFC entity registry** lists financial firms but not their websites
4. **The gap**: You cannot go from "company name" → "email domain" via government registry
5. **Workaround**: Use Google search `"{company name}" site:ae OR site:com` + extract domain from results

**Recommended CLI approach:**
```python
async def resolve_company_domain(company_name: str) -> str | None:
    """
    Resolve UAE company name to email domain.
    Government registries don't provide this, so use web search.
    """
    # Step 1: Try exact match with known UAE domains
    known = check_known_domains(company_name)  # hardcoded map
    if known:
        return known
    
    # Step 2: Google search (or DuckDuckGo API — free)
    results = await search(f'"{company_name}" UAE official website')
    for result in results:
        domain = extract_domain(result.url)
        if is_likely_corporate_domain(domain):  # filter out linkedin, facebook, etc.
            # Step 3: Verify with MX record check
            if await has_mx_records(domain):
                return domain
    
    # Step 4: Try .ae and .com variations of company name
    for tld in ['.ae', '.com']:
        candidate = slugify(company_name) + tld
        if await has_mx_records(candidate):
            return candidate
    
    return None
```

---

### 12G. GOOGLE DORKING FOR UAE RECRUITERS

**High-Value UAE-Specific Search Queries:**

```python
UAE_RECRUITER_DORKS = {
    # Find recruiter email addresses directly
    'email_direct': [
        '"recruiter" "@emirates.com" OR "@etihad.ae" OR "@adnoc.ae" intext:email',
        '"talent acquisition" UAE "@gmail.com" OR "@outlook.com"',  # independent recruiters
        '"recruitment consultant" Dubai "@charterhouseme.com" OR "@bacme.com"',
        'site:linkedin.com/in "recruiter" "Dubai" "email" OR "contact"',
    ],
    
    # Find job postings with recruiter contact info
    'job_posting_contacts': [
        'site:linkedin.com/jobs "recruiter" "Dubai" "contact" OR "email"',
        'site:bayt.com "recruitment" "UAE" "contact" OR "email"',
        'site:naukrigulf.com "HR" "UAE" "contact"',
        '"walk in interview" Dubai "email" OR "contact" recruiter',
    ],
    
    # Find recruiter profiles on agency websites
    'agency_profiles': [
        'site:heidrick.com "Dubai" consultant',
        'site:kornferry.com "Middle East" consultant',
        'site:charterhouseme.com "our team" OR "consultant"',
        'site:bacme.com "team" OR "consultant"',
    ],
    
    # Find recruiter WhatsApp numbers (GCC-specific!)
    'whatsapp': [
        '"recruiter" Dubai "WhatsApp" "+971" OR "+9715"',
        '"walk in interview" UAE "WhatsApp" contact',
        '"recruitment agency" Dubai "+971" contact',
        'site:dubizzle.com "recruitment" "+971"',
    ],
    
    # Find CVs/resumes of recruiters (to get their contact info)
    'recruiter_cvs': [
        'filetype:pdf "recruiter" OR "recruitment consultant" "Dubai" "email"',
        'filetype:doc "talent acquisition" "UAE" "contact"',
        'intitle:resume "recruiter" "Dubai" OR "Abu Dhabi"',
    ],
    
    # Find company email patterns
    'email_patterns': [
        '"@emirates.com" "recruitment" OR "talent acquisition" OR "HR"',
        '"@adnoc.ae" "careers" OR "recruitment" OR "HR"',
        '"@emaar.ae" OR "@emaar.com" "recruitment" OR "HR"',
        '"*.charterhouseme.com" email pattern',  # from email permutation tools
    ],
    
    # UAE-specific job boards
    'job_boards': [
        'site:gulftalent.com "recruiter" OR "HR" contact',
        'site:bayt.com "recruitment" "Dubai" contact',
        'site:naukrigulf.com "HR" "contact" Dubai',
        'site:expatriates.com "recruitment" Dubai email',
    ],
    
    # Conference/event speaker lists (high-value contacts)
    'events': [
        'site:hrse-me.com speaker OR exhibitor "recruitment"',
        '"HR Summit" Dubai speaker recruiter contact',
        '"CIPD" UAE "recruitment" contact email',
    ],
}

# Rate-limited query builder for CLI tool
def build_dork_query(category: str, **kwargs) -> str:
    """Build Google dork queries with UAE-specific patterns."""
    if category in UAE_RECRUITER_DORKS:
        queries = UAE_RECRUITER_DORKS[category]
        return queries  # return all queries in category
    return []
```

**Important caveats:**
1. Google rate-limits automated queries heavily (use DuckDuckGo API or SerpAPI for automation)
2. `site:linkedin.com` queries work but LinkedIn blocks scraping — use for discovery only
3. WhatsApp numbers in search results are a **GCC goldmine** — not available in Western markets
4. `filetype:pdf` and `filetype:doc` queries find CVs of recruiters themselves
5. Always include "+971" (UAE country code) and "+9715" (mobile prefix) in phone number searches

---

### 12H. SMTP VERIFICATION FOR UAE DOMAINS

**Do UAE mail servers accept RCPT TO probes?**

| Domain / Provider | Accepts VRFY? | Accepts RCPT TO? | Catch-All? | Notes |
|-------------------|--------------|-------------------|------------|-------|
| **M365 (outlook.com)** | ❌ No | ❌ Returns 250 for ALL | ⚠️ Yes (most) | Microsoft accepts everything at SMTP level → RCPT TO probe **unreliable** |
| **Google Workspace** | ❌ No | ⚠️ Sometimes | ⚠️ Some | Google may accept or reject. Inconsistent. Better than M365 but not reliable. |
| **On-premise Exchange** | ⚠️ Sometimes | ⚠️ Sometimes | Varies | Legacy government servers sometimes leak info via VRFY/RCPT TO |
| **Etisalat hosted** | ❌ No | ⚠️ Mixed | Some | Etisalat's mail hosting varies by customer config |
| **du hosted** | ❌ No | ⚠️ Mixed | Some | Similar to Etisalat |

**The M365 Problem (affects ~65-70% of UAE targets):**
Microsoft's email infrastructure accepts RCPT TO for virtually ANY address at a domain. This means:
- `nonexistent.person12345@emirates.com` → SMTP returns `250 2.1.5 Recipient OK`
- **You CANNOT verify email existence via SMTP against M365-hosted domains**
- This makes traditional SMTP verification useless for most UAE corporate emails

**Recommended verification strategy for CLI tool:**

```python
async def verify_uae_email(email: str, domain: str) -> dict:
    """
    Multi-layered email verification for UAE domains.
    SMTP alone is insufficient for M365/Google Workspace.
    """
    result = {'email': email, 'valid': None, 'confidence': 0, 'method': None}
    
    mx_hosts = await get_mx_records(domain)
    provider = detect_provider(mx_hosts)
    
    if provider == 'm365':
        # SMTP verification WILL NOT WORK for M365
        # Use alternative verification methods:
        
        # Method 1: Check Have I Been Pwned / breach databases
        if await check_breach_database(email):
            result['valid'] = True
            result['confidence'] = 0.9
            result['method'] = 'breach_database'
            return result
        
        # Method 2: Try Gravatar / Google profile / social lookup
        if await check_social_profiles(email):
            result['valid'] = True
            result['confidence'] = 0.85
            result['method'] = 'social_profile'
            return result
        
        # Method 3: Check if email appears in Google search results
        if await check_google_indexed(email):
            result['valid'] = True
            result['confidence'] = 0.8
            result['method'] = 'google_indexed'
            return result
        
        # Method 4: Pattern match against known format for domain
        if matches_known_pattern(email, domain):
            result['valid'] = 'likely'
            result['confidence'] = 0.6
            result['method'] = 'pattern_match'
            return result
        
        result['valid'] = 'unknown'
        result['confidence'] = 0.3
        result['method'] = 'cannot_verify_m365'
        
    elif provider == 'google_workspace':
        # Google Workspace is slightly better but still unreliable
        # Try SMTP first, then fall back to same methods
        smtp_result = await smtp_rcpt_to_probe(email, mx_hosts)
        if smtp_result['accepted'] == False:
            result['valid'] = False
            result['confidence'] = 0.8
            result['method'] = 'smtp_rejected'
            return result
        
        # If accepted, it might be catch-all — use other methods
        result = await fallback_verification(email, result)
        
    elif provider == 'on_premise':
        # Best case for SMTP verification
        smtp_result = await smtp_rcpt_to_probe(email, mx_hosts)
        if smtp_result.get('vrfy_supported'):
            vrfy_result = await smtp_vrfy(email, mx_hosts)
            if vrfy_result['found']:
                result['valid'] = True
                result['confidence'] = 0.9
                result['method'] = 'vrfy'
                return result
        
        if smtp_result['accepted'] == False:
            result['valid'] = False
            result['confidence'] = 0.85
            result['method'] = 'smtp_rejected'
            return result
        
        result = await fallback_verification(email, result)
    
    return result

def detect_provider(mx_hosts: list[str]) -> str:
    """Detect email provider from MX records."""
    mx_str = ' '.join(mx_hosts).lower()
    if 'outlook.com' in mx_str or 'protection.outlook.com' in mx_str:
        return 'm365'
    elif 'google.com' in mx_str or 'googlemail.com' in mx_str:
        return 'google_workspace'
    elif 'zoho.com' in mx_str:
        return 'zoho'
    else:
        return 'on_premise'
```

**Common UAE MX Hosts:**

| Company | MX Record | Provider |
|---------|-----------|----------|
| Emirates | `emirates-com.mail.protection.outlook.com` | M365 |
| Etihad | `etihad-ae.mail.protection.outlook.com` | M365 |
| ADNOC | `adnoc-ae.mail.protection.outlook.com` | M365 |
| DEWA | `mail1.dewa.gov.ae` (custom) | On-prem Exchange |
| Emaar | `emaar-ae.mail.protection.outlook.com` | M365 |
| Meraas | `meraas-com.mail.protection.outlook.com` | M365 |
| DP World | `dpworld-com.mail.protection.outlook.com` | M365 |
| Etisalat | `mx.etisalat.ae` (custom) | On-prem / Hybrid |
| du | `du-aemx2.com` (custom) | Custom / M365 hybrid |

**Key takeaway for CLI tool:**
> **For UAE/GCC, SMTP verification is nearly useless for the dominant provider (M365).** The tool MUST use alternative verification: breach databases, social profile lookups, Google indexing, and pattern matching. Only on-premise Exchange installations (DEWA, Etisalat, some government) respond accurately to RCPT TO probes. Budget ~65% of UAE email verifications as "unverifiable" via SMTP alone.

---

### 12I. SUMMARY: CLI TOOL IMPLEMENTATION PRIORITIES

| Priority | Feature | Why | Effort |
|----------|---------|-----|--------|
| **P0** | Arabic name → email permutation generator | 30%+ of UAE recruiters have Arabic names | Medium |
| **P1** | MX-based provider detection (M365 vs Google vs on-prem) | Determines verification strategy | Low |
| **P1** | Known domain map for top 50 UAE employers/agencies | Skip DNS lookup for known entities | Low |
| **P1** | M365-aware verification (skip SMTP, use alternatives) | SMTP returns false positives for M365 | Medium |
| **P2** | UAE Google dork query library | Free discovery of recruiter contacts | Low |
| **P2** | WhatsApp number extraction (+9715 pattern) | Primary GCC recruiter channel | Low |
| **P3** | ATS URL pattern detection (Taleo/SF/PageUp) | Reveals recruiter names in job postings | Medium |
| **P3** | DMCC directory scraper | Free company→website mapping | Medium |
| **P4** | `.ae` / `.com` domain fallback resolution | UAE companies often own both TLDs | Low |
