"""
Comprehensive Candidate Profile for Brandon Ruiz
Used by scorer.py and n8n prompts
"""

CANDIDATE_FULL_PROFILE = """
=============================================================================
BRANDON RUIZ - COMPLETE PROFESSIONAL PROFILE
=============================================================================

CONTACT:
- Location: Anaheim / Orange County, CA
- GitHub: github.com/brandonrz369
- Available for: On-site (OC/LA area), Hybrid, Limited Remote

=============================================================================
PROFESSIONAL EXPERIENCE
=============================================================================

LB COMPUTER HELP (Owner / IT Support Technician) | Apr 2025 - Present
─────────────────────────────────────────────────────────────────────────────
Built an MSP from zero to 130+ customers and $50K revenue.

BUSINESS DEVELOPMENT & MARKETING:
- Launched with $0 budget using Yelp's free ad credit for initial visibility
- Posted on Craigslist and Facebook community groups for local reach
- Scaled to Google Ads campaigns - this drove significant customer acquisition
- Grew through reputation - organic referrals became primary lead source
- Managed all operations: sales, service delivery, invoicing (Square), scheduling

B2B EMERGENCY IT SUPPORT:
- Provided emergency IT support to dozens of businesses:
  * Subway franchise locations - POS and network issues
  * Gas stations - complex network outages affecting payment systems
  * Professional offices - server failures, connectivity issues
- Diagnosed and resolved problems under pressure - businesses losing money every minute
- Developed ability to quickly assess unfamiliar environments and isolate issues
- Built reputation for solving problems other techs couldn't figure out
- Demonstrated ability to work across multiple strange spectrums of knowledge

REMOTE MANAGEMENT:
- Deployed and managed N-Able RMM agents across multiple client environments
- Provided proactive monitoring, patch management, and remote remediation
- Managed multiple businesses remotely simultaneously

─────────────────────────────────────────────────────────────────────────────
PRIMARY CLIENT - MARINA SHIPYARD | Jul 2024 - Present
Contract Value: $17,000 Year 1 ($975/month + $4,950 one-time migration fee)
─────────────────────────────────────────────────────────────────────────────
Executed complete MSP transition from All Covered (large national MSP) to my 
own management. Full infrastructure modernization with zero downtime.

BEFORE STATE (All Covered MSP):
- Email Security: ProofPoint (third-party, MX routing through ppe-hosted.com)
- DNS: Rackspace nameservers - no direct control
- Antivirus: BitDefender via N-Able (MSP controlled)
- Web Filtering: Cisco Umbrella
- Backup: All Covered Cloud (proprietary, expensive)
- Remote Management: N-Able agent (MSP controlled)
- M365: Business Standard, managed by All Covered CSP
- Documentation: Minimal/scattered

AFTER STATE (My Management):
- Email Security: Microsoft Defender for Office 365 (native, integrated)
- DNS: GoDaddy (direct client control)
- Antivirus: BitDefender GravityZone (own tenant)
- Web Filtering: DNS-based + Microsoft Defender
- Backup: Backblaze B2 (~$5/TB/month vs proprietary pricing)
- Remote Management: SSL VPN + iDRAC + direct management
- M365: Business Premium, CSP transferred to me
- Documentation: Comprehensive guides, network diagrams, quick reference cards

PROJECT 1: Complex DNS & Email Migration
- Challenge: Domain at GoDaddy, DNS hosted on Rackspace nameservers, email 
  routed through ProofPoint before reaching M365, previous MSP engineer on 
  vacation during critical transition
- Solution: Coordinated with outgoing MSP engineer (Brett), obtained complete 
  DNS record export, documented everything, planned migration
- Technical Details:
  * Identified and documented: 2 A records, 8 CNAME records, 2 MX records, 
    2 SRV records, 5 TXT records
  * Updated SPF from ProofPoint inclusion to Microsoft-only
  * Configured autodiscover, enterprise enrollment for device management
- Result: Simplified architecture, reduced attack surface, direct client control

PROJECT 2: Enterprise Backup Infrastructure Migration
- Challenge: Previous MSP terminating cloud storage service, client faced 
  potential data loss and backup gaps
- Solution: Evaluated multiple providers (AWS S3, Azure Blob, Backblaze B2, 
  Wasabi), selected Backblaze B2 for cost-effectiveness
- Technical Implementation:
  * Created encrypted bucket with Object Lock (ransomware protection)
  * Configured application keys with least-privilege access
  * Created comprehensive migration guide for Veeam reconfiguration
  * Maintained existing Synology NAS backups as redundancy during transition
- Cost Savings: From proprietary pricing to ~$5/TB/month

PROJECT 3: Network Infrastructure Documentation & Remote Access
- Challenge: Complex dual-WAN environment with Fortinet SD-WAN, multiple 
  network segments, various VM access methods, minimal existing documentation
- Solution: Created comprehensive technical documentation from scratch:
  * Network topology diagrams
  * Field technician quick reference card
  * Step-by-step access procedures (SSL VPN, iDRAC, ESXi console)
  * Troubleshooting decision trees
  * FortiGate command references

PROJECT 4: Microsoft 365 License Optimization
- Challenge: 7 Business Standard licenses managed by previous MSP, expiring 
  April 10, 2025, with Microsoft price increases effective April 1
- Solution: Coordinated CSP transfer, upgraded users to Business Premium for 
  enhanced security features (Defender for Office 365, Intune capabilities)

TECHNICAL ENVIRONMENT MANAGED:
Network Infrastructure:
- Dual WAN Configuration:
  * Frontier (Primary): 1Gbps fiber
  * ECCO Wireless (Secondary): 100Mbps backup
- Fortinet 60F Firewall (192.168.0.1)
  * SD-WAN configured for failover/load balancing
  * SSL VPN for remote access
  * Managing two internal networks
- Main LAN: 192.168.0.0/24
- Secondary LAN: 10.10.10.0/24

Virtualization:
- Dell PowerEdge T350 (192.168.0.11)
- VMware ESXi 8.0.3
- iDRAC (192.168.0.10) for remote management
- VMs:
  * IEMS-DC01V (Domain Controller + Veeam)
  * IEMS-FS01V (File Server)
  * OPS-INDEL-V (Ubuntu Linux)

Storage:
- Synology NAS (192.168.0.40) - Veeam repository
- Backblaze B2 cloud backup with Object Lock

Users/Workstations: 7 total

─────────────────────────────────────────────────────────────────────────────
GEEKS-ON-SITE (IT Specialist) | Jun 2021 - Oct 2021
─────────────────────────────────────────────────────────────────────────────
- Dispatched to residential and small business locations for break-fix support
- Diagnosed hardware failures, malware infections, network connectivity issues
- Performed data recovery, system rebuilds, and hardware upgrades
- Developed customer communication skills - explaining technical issues to 
  non-technical users
- Consistently received positive customer feedback

─────────────────────────────────────────────────────────────────────────────
JFG SYSTEMS (IT Consultant - MSP) | Feb 2019 - Mar 2019
─────────────────────────────────────────────────────────────────────────────
- Worked at established MSP learning professional service delivery standards
- Supported multiple client environments with varying technology stacks
- Gained exposure to MSP business operations, ticketing workflows, SLAs
- Foundation for launching my own MSP with professional standards

─────────────────────────────────────────────────────────────────────────────
RADMAX (Contract - Penetration Testing) | During Fusion tenure (2016-2017)
─────────────────────────────────────────────────────────────────────────────
- Contracted at age 18 to perform penetration testing on company network
- Utilized Metasploit framework for vulnerability assessment
- Applied knowledge from years of self-taught security research
- Configured Amazon AWS VPS to host the penetration testing environment
- Provided C-level executives with real-time dashboard to monitor attack progress
- Delivered findings and recommendations to stakeholders
- Early professional validation of security skills developed since childhood

─────────────────────────────────────────────────────────────────────────────
FUSION CONTACT CENTERS (IT Support → Escalation Team) | Aug 2016 - Aug 2017
─────────────────────────────────────────────────────────────────────────────
Started as Tier 1 help desk. PROMOTED TO ESCALATION TEAM AT AGE 18.
Handled higher-tier tickets that frontline support couldn't resolve.
Worked with enterprise-grade network environments across diverse clients.

ENTERPRISE FIREWALL EXPERIENCE:
- Troubleshot nearly every major firewall brand in production environments:
  * Cisco ASA
  * Fortinet FortiGate
  * SonicWall
  * Palo Alto
  * Meraki
  * pfSense
- Diagnosed and resolved WAN connectivity issues under pressure
- Configured and debugged firewall rules for various applications

VOIP/UNIFIED COMMUNICATIONS:
- Extensive 8x8 VoIP troubleshooting
- SIP trunk configuration and debugging
- Resolved "phones are down" emergencies affecting entire offices
- WAN rules, QoS, and network configuration for voice traffic
- When 50 phones go down and a business is paralyzed, you learn to isolate 
  issues FAST
- Figured out everything under the sun to get 8x8 to work on client systems

- Exposure to massive variety of enterprise environments and configurations
- Developed rapid troubleshooting skills under extreme pressure

─────────────────────────────────────────────────────────────────────────────
ADDITIONAL WORK HISTORY (Demonstrating Work Ethic)
─────────────────────────────────────────────────────────────────────────────
- LAZ Parking (Supervisor) | Nov 2022 - Present
- Randstad / Innovation Bakery (Warehouse/Machine Operator) | Oct 2022 - Present
- DoorDash (Driver/Gig Work) | Oct 2021 - Present
- Valeo (Warehouse/Machine Operator) | Apr 2019 - Dec 2019

=============================================================================
TECHNICAL SKILLS
=============================================================================

INFRASTRUCTURE & SYSTEMS:
- Windows Server 2016/2019/2022
- Active Directory, Group Policy, DNS, DHCP
- VMware ESXi 8.x, vCenter basics, VM provisioning and management
- Dell PowerEdge servers, iDRAC remote management
- Synology NAS configuration and management

NETWORKING & FIREWALLS:
- Multi-vendor production experience:
  * Fortinet FortiGate (primary at Marina)
  * Cisco ASA
  * SonicWall
  * Palo Alto
  * Meraki
  * pfSense
- TCP/IP, VLANs, routing, dual-WAN failover, SD-WAN
- SSL VPN configuration and troubleshooting
- Network documentation and topology diagrams

VOIP & UNIFIED COMMUNICATIONS:
- 8x8 VoIP troubleshooting and configuration (extensive)
- SIP trunk debugging
- WAN rules for voice traffic
- QoS configuration for call quality
- Enterprise phone system support (multi-vendor)
- Emergency "phones down" resolution under pressure

MICROSOFT 365 & CLOUD:
- M365 Administration: Exchange Online, SharePoint, Teams, OneDrive
- Microsoft Defender for Office 365
- Azure AD basics, Intune fundamentals
- CSP licensing and tenant management
- SPF/DKIM/DMARC email authentication
- AWS (VPS configuration for pen testing)

BACKUP & DISASTER RECOVERY:
- Veeam Backup & Replication
- Backblaze B2 with Object Lock (ransomware protection)
- Backup strategy design, retention policies, restore testing
- Synology NAS as backup repository

SECURITY & PENETRATION TESTING:
- Metasploit framework (professional pen testing experience)
- Network vulnerability assessment
- AWS VPS configuration for security testing
- Endpoint protection (BitDefender GravityZone, Microsoft Defender)
- MFA implementation, security awareness
- Security-first mindset from early self-teaching

TOOLS & AUTOMATION:
- RMM: N-Able (deployment, monitoring, remote access)
- Python scripting and automation
- n8n workflow automation
- AI/LLM integration (Claude API, workflow design)
- Invoicing: Square
- Documentation: Network diagrams, runbooks, quick reference cards

=============================================================================
PERSONAL PROJECTS & TECHNICAL BACKGROUND
=============================================================================

AUTONOMOUS JOB APPLICATION AGENT (Current Project - 2025)
─────────────────────────────────────────────────────────────────────────────
Built a fully autonomous system that scrapes job postings, scores them for 
relevance using AI, generates tailored resumes/cover letters, and will 
eventually auto-apply. THIS APPLICATION WAS GENERATED BY THAT SYSTEM.

Architecture:
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ Scrape  │ → │  Score  │ → │Generate │ → │  Apply  │
│ JobSpy  │   │ Gemini  │   │ Gemini  │   │BrowserUse│
└─────────┘   └─────────┘   └─────────┘   └─────────┘

Tech Stack:
- Python (JobSpy for scraping, proxy rotation)
- n8n workflow automation (self-hosted on Hetzner VPS)
- Google Gemini AI: 2.5 Flash for job scoring, Gemini for document generation
- Gotenberg for HTML-to-PDF conversion
- Docker containerization
- Deduplication system (job ID, URL, company+title hash)
- Queue management (pending, applied, failed, manual)

Demonstrates: API integration, workflow design, cost optimization
(using cheaper models where appropriate), error handling, systems thinking.

GitHub: github.com/brandonrz369/job-agent

CRAIGSLIST SCRAPER WITH PROXY ROTATION
─────────────────────────────────────────────────────────────────────────────
- Built Python scraper aligned with skillsets
- Scrapes Craigslist for opportunities
- Implements proxy switching to avoid rate limiting
- Built with AI assistance

GITHUB PROJECTS (github.com/brandonrz369)
─────────────────────────────────────────────────────────────────────────────
1. pokerresearch - C++/Python Poker HUD & Strategy Agent
   - Prototypes a poker heads-up display and action-recommendation agent
   - Features: state ingestion, game modeling, baseline strategies, overlay
   - Includes hooks for LLM integration (pointing HUD at internal LLM)
   - Dataset helpers for research
   - University of Nevada research project

2. lbcom & smart-services-it - Business Websites
   - Full Next.js/Tailwind CSS website templates
   - Clone, install, customize, deploy workflow
   - Deployment to Vercel or Netlify
   - Custom domain configuration

3. Gemini-Scraper
   - Python-dominated scraper project
   - Includes Python and C/Cython code
   - Associated site hosted on Vercel

4. gravy-scraper & gravybaby
   - Python automation/scraping tools
   - Job board scraping with proxy rotation

5. Other repositories:
   - powerpoint - Firebase tools setup
   - mar - Project with Anthropic Claude assistance

XDA DEVELOPERS CONTRIBUTIONS (2013-2015) - Age 16
─────────────────────────────────────────────────────────────────────────────
[1] N.E.O.N. R.O.M. - Verizon Galaxy Note 3 (Build 3 Version 5)
    Started December 2, 2013 in Android Development section
    
    - Created custom ROM described as "go-to" option for users seeking 
      "tweaked, slim, stock, fast rom with OUTSTANDING battery life"
    - Removed 189 pre-installed apps (717 MB saved)
    - Sub-500MB ROM, Knox-free
    - Disabled Samsung annoyances
    - Added AOSP-themed features:
      * ICS-style icons
      * 4.4 sound pack
      * AOSP lock screen
    - Suite of performance tweaks:
      * 5×5 launcher with 6-icon dock
      * Sound-boost hack
      * Infinite launcher scroll
      * Disabled scrolling cache for smoother performance
    - Pre-rooted with BusyBox, zipalignment, init.d support
    - Credited collaborators (sbreen94, foreverloco, XzxBATTxzX, AngryManMLS)
    - Provided download links for ROM, add-on theme, Samsung camera module
    - Maintained updates and community support

[2] Petition to Unlock Bootloader (October 20, 2013)
    - Organized community petition urging Samsung and Verizon to unlock 
      Galaxy Note 3 bootloader
    - Encouraged users to sign Change.org petition
    - Listed executive names, phone numbers, and email addresses for 
      direct pressure campaign
    - Community activism for user freedom

[3] Safestrap Installation Guide (November 11, 2013)
    - Authored detailed guide explaining how to install custom ROMs over 
      stock partition without wasting space or triggering Knox
    - Specified prerequisites: rooted N900V, Safestrap v3.62, Odin
    - Step-by-step instructions for backup, ROM slot creation, restoration

[4] Note 3 KitKat Root Guide (June 16, 2014)
    - Shared instructions on using Geohot's Towelroot exploit
    - Root on Note 3 running Android 4.4.2
    - Concise, accessible instructions for community

[5] HTC One M8 S-OFF Guide Contribution (October 18, 2015)
    - Sought and shared advice on updating firmware while preserving 
      S-OFF status and user data

SUMMARY OF XDA CONTRIBUTIONS:
- Demonstrates deep technical curiosity at age 16
- Documentation skills - created guides others could follow
- Community contribution and collaboration
- System optimization and customization
- Activism for user rights and device freedom

ORIGIN STORY
─────────────────────────────────────────────────────────────────────────────
Self-taught from necessity. As a teenager with an overbearing mother, 
technology became my outlet. When I had issues with parental controls, I 
installed Linux or other tools to remove them. When we didn't have WiFi 
anymore, I bought an antenna off eBay and burned a Linux distro to access 
neighbors' networks. Got really good at it too.

This problem-solving mindset - finding technical solutions to real 
constraints - has defined my approach to IT ever since. I don't wait for 
permission or training; I figure it out.

=============================================================================
WHAT MAKES ME DIFFERENT
=============================================================================

1. PROMOTED AT 18: Moved to escalation team at Fusion handling tickets that
   stumped experienced techs. Employers recognized my abilities early.

2. SECURITY BACKGROUND: Professional pen testing contract at 18. Self-taught
   from childhood. I think like an attacker, defend like a pro.

3. MULTI-VENDOR FIREWALL FLUENCY: Cisco, Fortinet, SonicWall, Palo Alto, 
   Meraki, pfSense - all in production environments. Not just one vendor.

4. ENTREPRENEURIAL: Built a real MSP, won a $17K contract, handled emergency
   outages where businesses were losing money. I understand business impact.

5. VOIP UNDER PRESSURE: When 50 phones go down and a business is paralyzed,
   I've been the one isolating SIP issues. I know 8x8 inside and out.

6. FULL STACK: Help desk to pen testing to MSP owner. I've worked every 
   level and understand how they connect.

7. DOCUMENTATION OBSESSED: I create network diagrams, runbooks, and quick
   reference cards because good documentation prevents 3am emergencies.

8. BUILDS TOOLS: Not just uses them. This job application came from an
   AI-powered system I built myself. That's how I approach problems.

9. ROM DEVELOPER AT 16: Was publishing custom Android ROMs with thousands
   of downloads while still in high school. Deep technical curiosity.

10. WORKS HARD: Maintained IT career development while working supervisor,
    warehouse, and gig jobs. Whatever it takes.

=============================================================================
EDUCATION & CERTIFICATIONS
=============================================================================
- Currently studying for AWS Cloud Practitioner
- Continuous self-education via documentation, labs, and real-world projects
- No formal degree - 100% self-taught and battle-tested

=============================================================================
BROADER CAPABILITIES (Beyond Technical)
=============================================================================

BUSINESS OWNERSHIP & OPERATIONS:
- Full P&L responsibility running LB Computer Help
- Client acquisition, pricing strategy, contract negotiation ($17K deal)
- Marketing: Google Ads campaigns, Yelp, Facebook, Craigslist
- Scaled solo operation from $0 to $50K revenue

TECHNICAL WRITING & DOCUMENTATION:
- Network topology diagrams
- Runbooks, SOPs, migration guides
- Quick reference cards for field techs
- Troubleshooting decision trees
- Obsessive about good documentation

AI & AUTOMATION (Current Focus):
- Building autonomous job application system using:
  - Google Gemini API (2.5 Flash for scoring, Gemini for document generation)
  - n8n workflow automation (self-hosted)
  - Python scripting
  - Browser automation
- Prompt engineering for consistent LLM outputs
- Agentic workflow design
- Cost optimization across AI models

PROJECT MANAGEMENT:
- Scoped and executed full MSP-to-MSP transition
- Coordinated multi-vendor handoffs
- Zero-downtime migrations
- Timeline management around hard deadlines

LEARNING SPEED:
- 100% self-taught, no formal training
- Learns new systems rapidly under pressure
- Comfortable being dropped into unfamiliar environments
- Track record: promoted to escalation team at 18, pen testing contract at 18, custom ROM developer at 16

=============================================================================
"""

# Use full profile for scoring too (Gemini 2.5 Flash can handle it)
CANDIDATE_SCORING_PROFILE = """
Brandon Ruiz - IT Professional / MSP Founder

EXPERIENCE:
- LB Computer Help (MSP) | 2025: 130+ customers, $50K revenue, Marina Shipyard $17K contract
- Fusion Contact Centers | 2016-2017: PROMOTED TO ESCALATION AT 18, enterprise firewalls (Cisco/Fortinet/SonicWall/Palo Alto/Meraki/pfSense), VoIP/8x8/SIP
- Radmax | 2016-2017: Pen testing contract at 18, Metasploit, AWS
- Geeks-On-Site | 2021: Break-fix technician
- JFG Systems | 2019: MSP technician

SKILLS: Windows Server, AD, VMware ESXi, FortiGate, M365, Veeam, VoIP/SIP, Python, N-Able RMM

LOCATION: Anaheim / Orange County, CA | TARGET: $50-80K | No degree, studying AWS cert
"""
