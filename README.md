<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/HTMX-3D72D7?style=for-the-badge&logo=htmx&logoColor=white" alt="HTMX">
  <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS">
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
</p>

<h1 align="center">🏔️ Far Reach Jobs</h1>

<p align="center">
  <strong>An ethical job aggregator for remote Alaskan communities, bush villages, and tribal organizations.</strong><br>
  Find opportunities in places most job boards don't reach.
</p>

<p align="center">
  <a href="https://far-reach-jobs.tachyonfuture.com/">🌐 Live Site</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-contributing">🤝 Contributing</a> •
  <a href="ROADMAP.md">🗺️ Roadmap</a>
</p>

---

## 🎯 Why This Exists

Job seekers interested in remote Alaska face a **fragmented landscape** - positions are scattered across dozens of small employer websites, tribal organization portals, and government HR systems.

**Far Reach Jobs brings them together in one searchable place.**

We aggregate listings from bush villages, tribal organizations, rural hospitals, and small-town governments - then link you directly back to the original source to apply.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Smart Search** | Filter by keyword, city/community, and job type |
| 💾 **Save Jobs** | Track positions you're interested in |
| 🌙 **Dark Mode** | Easy on the eyes, day or night |
| 📱 **Mobile-First** | Responsive design that works everywhere |
| 🤖 **AI-Powered Setup** | Auto-detect CSS selectors for new job sources |
| ⏰ **Daily Updates** | Fresh jobs scraped at noon Alaska time |

---

## 🛠️ Tech Stack

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│          HTMX • Jinja2 Templates • Tailwind CSS        │
├─────────────────────────────────────────────────────────┤
│                      Backend                            │
│              FastAPI • SQLAlchemy • MySQL               │
├─────────────────────────────────────────────────────────┤
│                     Scraping                            │
│           httpx • BeautifulSoup • APScheduler          │
├─────────────────────────────────────────────────────────┤
│                    Deployment                           │
│           Docker Compose • Nginx Proxy Manager          │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/mbuckingham74/Far-Reach-Jobs.git
cd Far-Reach-Jobs

# Copy environment config
cp .env.example .env

# Create Docker network (first time only)
docker network create npm_default

# Start services
docker compose up -d --build
```

Then visit **http://localhost:8000** 🎉

> 📖 See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed setup instructions.

---

## 🤝 Contributing

We welcome contributions from developers of all skill levels!

<table>
  <tr>
    <td align="center">📋</td>
    <td><a href="CONTRIBUTING.md"><strong>Contributing Guide</strong></a><br>Setup and development guidelines</td>
  </tr>
  <tr>
    <td align="center">🗺️</td>
    <td><a href="ROADMAP.md"><strong>Roadmap</strong></a><br>Planned features and improvements</td>
  </tr>
  <tr>
    <td align="center">🐛</td>
    <td><a href="https://github.com/mbuckingham74/Far-Reach-Jobs/issues"><strong>Issues</strong></a><br>Open tasks and bug reports</td>
  </tr>
</table>

### 👋 Good First Issues

- 📍 Suggest new Alaska job sources via the "New Job Source" issue template
- ✅ Improve test coverage
- 🎨 UI/UX enhancements

---

## 👔 For Employers

Are you an employer in remote Alaska? We'd love to include your jobs!

Visit our **[For Employers](https://far-reach-jobs.tachyonfuture.com/employers)** page to:

- 📝 **Submit a single job** - Fill out a simple form
- 🔗 **Add your careers page** - We'll set up automatic scraping
- 📊 **Bulk import** - Upload a CSV with multiple organizations

> 🚫 Want to be excluded from scraping? [Open an issue](https://github.com/mbuckingham74/Far-Reach-Jobs/issues) and we'll remove your site.

---

## ⚙️ Admin Features

Far Reach Jobs includes a powerful admin panel for managing job sources:

<details>
<summary><strong>🤖 AI-Powered Scraper Configuration</strong></summary>

- **Analyze Page with AI** - Automatically suggests CSS selectors
- **Generate Custom Scraper** - AI creates Python code for complex sites
- **Bulk CSV Import** - Add dozens of sources at once

</details>

<details>
<summary><strong>📋 Adding a New Source</strong></summary>

1. Go to Admin Dashboard → Add Scrape Source
2. Enter the source name and base URL
3. Click **"Analyze Page with AI"** to auto-detect selectors
4. Review suggestions and click "Apply All"
5. Set a default location (e.g., "Bethel")
6. Save and test with a manual scrape

</details>

<details>
<summary><strong>📊 Bulk Import via CSV</strong></summary>

```csv
Source Name,Base URL,Jobs URL
City of Bethel,https://www.cityofbethel.net,https://www.cityofbethel.net/jobs
NANA Regional,https://nana.com,https://nana.com/careers
```

Upload via Admin Dashboard → Bulk Import from CSV. Duplicates are automatically skipped.

</details>

---

## 🙏 Ethics & Respect

- ✅ We respect `robots.txt` rules
- ✅ We identify ourselves as `FarReachJobs/1.0` in our User-Agent
- ✅ We honor crawl delays when specified
- ✅ We link directly to original listings (no job duplication)

---

## 📄 License

MIT © [Far Reach Jobs](https://github.com/mbuckingham74/Far-Reach-Jobs)

---

<p align="center">
  <strong>Built with ❤️ for Alaska's remote communities</strong><br>
  <sub>Connecting job seekers with opportunities in places most job boards don't reach</sub>
</p>
