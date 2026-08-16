# ResumeIQ

"Stop guessing, start landing interviews." A resume toolkit built with **Django, Python, HTML, CSS and vanilla JavaScript** — no frontend framework, no external AI API. Everything (parsing, scoring, matching) runs locally in plain Python.

## Tools included

1. **Resume Creator** — guided form (personal info, summary, repeatable work experience & education blocks, skills, certifications) that renders a clean, print-ready resume preview. Click "Download / Print PDF" to save it via the browser's print dialog.
2. **Resume Analyser** — upload a PDF / DOCX / TXT resume. The engine extracts the text, detects standard sections (contact info, summary, skills, experience, education, certifications), checks for quantified achievements and strong action verbs, and produces an ATS score out of 100 plus a section-by-section checklist.
3. **Resume Optimizer** — upload a resume and paste a job description. The engine extracts the most important keywords from the JD, checks which ones already appear in the resume, and shows a keyword match score plus the exact keywords you're missing.

## Pages

- **Home** (`/`) — hero + tool showcase
- **Tools** (`/tools/`) — all three tools in one place
- **About** (`/about/`) — mission & how it works
- **Contact** (`/contact/`) — working contact form (flash-messages on submit)
- **Log In** (`/login/`) / **Sign Up** (`/signup/`) — real Django auth (SQLite-backed), navbar switches to a user chip + Log Out once signed in


## Project structure

```
resumeiq/
├── manage.py
├── requirements.txt
├── resumeiq/              # Django project (settings, urls, wsgi)
└── tools/                 # Django app — all the actual logic
    ├── views.py            # request handling for the 3 tools + home page
    ├── urls.py
    ├── utils.py            # text extraction, ATS scoring, keyword matching
    ├── templates/tools/    # HTML (base + home + 3 tool pages)
    └── static/tools/       # CSS + JS (dark/teal theme, matches the design)
```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate        # creates db.sqlite3 for Log In / Sign Up
python manage.py runserver
```

Then open **http://127.0.0.1:8000/** in your browser. **Always use this exact address** (not `localhost:8000`) — browsers treat those as two different sites, so switching between them is why you'd otherwise get logged out on every restart. As long as you keep using the same address, your login now persists across restarts (session cookie lasts 30 days).

A SQLite database (`db.sqlite3`) is used only for the built-in Log In / Sign Up pages. The resume tools themselves never touch it — uploads are processed in memory only.

## Setting up Google Sign-In

1. Copy `.env.example` to a new file named `.env` in this folder (same level as `manage.py`).
2. Go to the [Google Cloud Console credentials page](https://console.cloud.google.com/apis/credentials), create a project if you don't have one, then click **Create Credentials → OAuth client ID**.
   - Application type: **Web application**
   - Authorized redirect URI: `http://127.0.0.1:8000/accounts/google/login/callback/`
3. Copy the generated **Client ID** and **Client Secret** into `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
4. Run `python manage.py migrate` again (allauth adds a couple of tables), then `python manage.py runserver`.
5. "Continue with Google" now appears on both the Log In and Sign Up pages.

## Setting up the Contact/Feedback form email

Right now feedback submitted through the Contact page is emailed to `resumeassistant7@gmail.com` via Gmail's SMTP server. To turn this on:

1. On the Gmail account you want to **send** from (this can be `resumeassistant7@gmail.com` itself, or any other Gmail account), turn on **2-Step Verification** in [Google Account → Security](https://myaccount.google.com/security).
2. Go to [Google Account → App Passwords](https://myaccount.google.com/apppasswords), create one for "Mail", and copy the 16-character password it gives you.
3. In your `.env` file, set:
   ```
   EMAIL_HOST_USER=your-sending-address@gmail.com
   EMAIL_HOST_PASSWORD=the16charapppassword
   ```
4. Restart the server. Submitting the form on the Contact page now emails `resumeassistant7@gmail.com` with the sender's name, email, subject and message (and sets Reply-To to the sender, so you can just hit Reply).

If `.env` isn't filled in, the form will show a friendly error instead of crashing.

## Notes

- File uploads are processed **in memory only** — nothing is written to disk or a database.
- Supported resume file types: `.pdf`, `.docx`, `.txt`.
- All scoring logic (ATS score, keyword matching, section detection) lives in `tools/utils.py` — tweak the keyword lists / weightings there to change how strict the scoring is.
- The theme (colors, fonts, layout) lives entirely in `tools/static/tools/css/style.css` using CSS variables at the top of the file, so re-theming is a one-file change.
