# Research Paper & Topic Recommendation System

A modern literature-review dashboard built for managing research themes, papers, findings, future work, and report generation in a single professional interface. The project is designed as a clean academic dashboard for presenting structured review work, tracking paper-level insights, and exploring related literature efficiently.

## Overview

This project combines:
- a polished frontend dashboard
- a Flask-based backend API
- SQLite-powered data persistence
- dynamic paper management and filtering
- real-time research discovery support
- report-ready summary generation

It is ideal for academic projects, seminar reports, literature review submissions, and research dashboard demos.

## Key Features

- Interactive overview dashboard with KPI cards and visual summaries
- Theme-based organization for research domains
- Full CRUD support for research papers
- Search and filtering by title, theme, and status
- Key findings management for strengths and open challenges
- Research gap editor and future-work tracker
- Reading list with personal notes and tags
- Real-time paper discovery via open scholarly APIs
- Export-ready report generation for academic presentation
- SQLite database with auto-initialization and seed data

## Tech Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Python + Flask
- Database: SQLite
- API style: RESTful JSON endpoints
- Deployment: local server or simple WSGI-compatible hosting

## Project Structure

```text
research-dashboard/
├── README.md
├── database/
│   ├── schema.sql
│   └── research_dashboard.db
└── backend-flask/
    ├── app.py
    ├── database.py
    ├── init_db.py
    ├── requirements.txt
    └── templates/
        └── index.html
```

## Quick Start

### 1) Open terminal and navigate to the project

```bash
cd "c:\Users\ARPIT KALE\Desktop\research-dashboard"
```

### 2) Install dependencies

```bash
cd backend-flask
pip install -r requirements.txt
```

### 3) Run the application

```bash
python app.py
```

### 4) Open the dashboard

Visit:

```text
http://127.0.0.1:5000/
```

The application will automatically create the SQLite database on first run if it does not already exist.

## Dashboard Modules

### Overview
- Total papers reviewed
- Publication span
- Theme distribution
- Year-wise trend analysis
- Key findings summary

### Research Papers
- Add, edit, and delete records
- Search and filter by status or theme
- View paper metadata and contribution details
- Refresh citation data when needed

### Discover Papers
- Search external sources for related research
- Retrieve metadata such as authors, venue, DOI, year, and abstract
- Explore topic-level publication trends
- Save relevant items to a reading list

### Themes
- Organize the literature into structured clusters
- Review paper counts per theme
- Generate literature summary text for each theme

### Key Findings & Future Work
- Maintain evidence-backed strengths and open problems
- Track actionable future research directions

### Research Gap
- Update the gap statement used in the report
- Generate a fresh analysis based on current records

### Settings & Reports
- Manage report metadata
- Prepare a presentation-friendly summary page

## API Highlights

The backend exposes REST endpoints such as:

- GET /api/dashboard/summary
- GET /api/papers
- POST /api/papers
- GET /api/themes
- GET /api/key-findings
- GET /api/future-work
- GET /api/research-gap
- PUT /api/report-meta

These APIs power the dashboard and allow the data to be managed from the frontend without a separate backend service.

## Notes on External Data

The project includes live search support using public research APIs, such as:
- Semantic Scholar
- CrossRef
- OpenAlex

This is useful for discovering relevant literature and checking citation trends, but public API availability may vary depending on network access and rate limits.

## Troubleshooting

### App does not open

Check whether the Flask server is running:

```bash
python app.py
```

If the port is already occupied, change the last line in the Flask app:

```python
app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)
```

Then open:

```text
http://127.0.0.1:5001/
```

### Database reset

If you want to start fresh:

```bash
cd backend-flask
python init_db.py
```

### Delete existing database

```bash
rm database/research_dashboard.db
```

Then rerun the app to recreate the database automatically.

## Deployment Notes

This project is lightweight and works well for local use, simple deployment, or hosting on a basic Python-capable server. It is designed to be easy to run without requiring external database setup.

## License

This project is licensed under the MIT License.

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Final Note

The project is structured to be clean, maintainable, and presentation-ready for academic or research dashboard use. It prioritizes clarity, usability, and a professional user experience.
