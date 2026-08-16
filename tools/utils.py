"""
tools/utils.py
----------------
Plain-Python engine that powers the Resume Analyser and Resume Optimizer.
No external services are called - everything runs locally.
"""
import random
import re
import string

# ---------------------------------------------------------------------------
# FILE TEXT EXTRACTION
# ---------------------------------------------------------------------------

def extract_text_from_upload(uploaded_file):
    """Return plain text from an uploaded .pdf, .docx or .txt file."""
    name = uploaded_file.name.lower()

    if name.endswith('.pdf'):
        return _extract_pdf(uploaded_file)
    if name.endswith('.docx'):
        return _extract_docx(uploaded_file)
    if name.endswith('.txt'):
        return uploaded_file.read().decode('utf-8', errors='ignore')

    raise ValueError('Unsupported file type. Please upload a PDF, DOCX or TXT file.')


def _extract_pdf(uploaded_file):
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # fallback
        except ImportError as exc:
            raise ImportError(
                "PDF support requires 'pypdf' or 'PyPDF2'. "
                "Install with: pip install pypdf"
            ) from exc

    reader = PdfReader(uploaded_file)
    text = []
    for page in reader.pages:
        text.append(page.extract_text() or '')
    return '\n'.join(text)


def _extract_docx(uploaded_file):
    try:
        import docx
    except ImportError as exc:
        raise ImportError(
            "DOCX support requires 'python-docx'. "
            "Install with: pip install python-docx"
        ) from exc

    document = docx.Document(uploaded_file)
    return '\n'.join(p.text for p in document.paragraphs)


# ---------------------------------------------------------------------------
# SECTION DETECTION
# ---------------------------------------------------------------------------

SECTION_KEYWORDS = {
    'contact_info': [r'@', r'\+?\d[\d\s\-\(\)]{7,}\d', r'linkedin\.com'],
    'summary': [r'\bsummary\b', r'\bobjective\b', r'\bprofile\b'],
    'skills': [r'\bskills\b', r'\btechnical skills\b', r'\bcompetencies\b'],
    'experience': [r'\bexperience\b', r'\bemployment\b', r'\bwork history\b'],
    'education': [r'\beducation\b', r'\bacademic\b', r'\bqualifications\b'],
    'certifications': [r'\bcertification', r'\bcertificate', r'\blicense'],
}

QUANTIFIED_ACHIEVEMENT_PATTERN = re.compile(
    r'(\d+(\.\d+)?\s?%|\$\s?\d+|\b\d+\+?\s?(years|months|users|clients|projects|team|people)\b)',
    re.IGNORECASE,
)

ACTION_VERBS = [
    'led', 'built', 'created', 'managed', 'designed', 'developed', 'launched',
    'improved', 'reduced', 'increased', 'implemented', 'delivered', 'optimized',
    'automated', 'coordinated', 'mentored', 'analyzed', 'analysed', 'negotiated',
]

STOPWORDS = set("""
a an the and or but if then so to of in on for with at by from as is are was
were be been being this that these those it its it's your you our we they
""".split())


def _find_sections(text_lower):
    found = {}
    for section, patterns in SECTION_KEYWORDS.items():
        found[section] = any(re.search(p, text_lower) for p in patterns)
    return found


COMMON_ATS_KEYWORDS = [
    'communication', 'leadership', 'teamwork', 'collaboration', 'problem solving',
    'analytical', 'data analysis', 'project management', 'agile', 'scrum',
    'python', 'java', 'javascript', 'sql', 'excel', 'microsoft office',
    'git', 'cloud', 'aws', 'azure', 'customer service', 'sales',
    'research', 'presentation', 'budgeting', 'strategy', 'marketing',
    'time management', 'cross-functional', 'stakeholder', 'documentation',
    'training', 'mentoring', 'planning', 'reporting', 'negotiation',
]

CLICHE_PHRASES = [
    'hard worker', 'team player', 'go-getter', 'think outside the box',
    'results-driven', 'detail-oriented', 'self-starter', 'people person',
    'responsible for', 'duties included',
]

FIRST_PERSON_PATTERN = re.compile(r'\b(i|me|my|mine)\b', re.IGNORECASE)
BULLET_LINE_PATTERN = re.compile(r'^\s*[-•*▪●]\s+', re.MULTILINE)


def _keyword_match(text_lower):
    found = [kw for kw in COMMON_ATS_KEYWORDS if kw in text_lower]
    missing = [kw for kw in COMMON_ATS_KEYWORDS if kw not in text_lower][:10]
    score = round((len(found) / len(COMMON_ATS_KEYWORDS)) * 100)
    return {'found': found, 'missing': missing, 'score': score}


def _content_quality(text, text_lower, word_count, has_quantified, action_verb_hits):
    bullet_lines = len(BULLET_LINE_PATTERN.findall(text))
    sentences = [s for s in re.split(r'[.!?]\s+', text) if s.strip()]
    avg_sentence_len = (word_count / len(sentences)) if sentences else 0
    passive_hits = len(re.findall(r'\b(was|were|been|being)\s+\w+ed\b', text_lower))

    items = [
        ('Uses quantified achievements (numbers, %, $)', has_quantified),
        ('Uses strong action verbs (led, built, improved...)', action_verb_hits >= 3),
        ('Uses bullet points instead of dense paragraphs', bullet_lines >= 3),
        ('Sentences are a reasonable length (under ~28 words on average)', avg_sentence_len <= 28),
        ('Minimal passive voice', passive_hits <= 3),
    ]
    passed = sum(1 for _, ok in items if ok)
    score = round((passed / len(items)) * 100)
    return {'score': score, 'items': items, 'bullet_lines': bullet_lines, 'avg_sentence_len': avg_sentence_len, 'passive_hits': passive_hits}


def _find_issues(text, text_lower, word_count, content):
    issues = []
    if FIRST_PERSON_PATTERN.search(text):
        issues.append('First-person pronouns (I, me, my) found — resumes read stronger without them.')
    hit_cliches = [p for p in CLICHE_PHRASES if p in text_lower]
    if hit_cliches:
        issues.append(f"Overused filler phrases detected: {', '.join(hit_cliches[:4])}.")
    if content['bullet_lines'] < 3:
        issues.append('Very few bullet points — dense paragraphs are harder for ATS parsers and recruiters to scan.')
    if content['avg_sentence_len'] > 28:
        issues.append('Some sentences run long — aim for punchy, scannable lines.')
    if content['passive_hits'] > 3:
        issues.append('Passive voice shows up often — lead with the action verb instead ("Led the team" not "The team was led by").')
    if word_count < 300:
        issues.append('Resume is on the short side — ATS and recruiters may read it as thin on experience.')
    elif word_count > 800:
        issues.append('Resume is quite long — trim it down so the strongest points aren\'t buried.')
    return issues


def _formatting_checks(sections, word_count, text):
    upper_words = re.findall(r'\b[A-Z]{4,}\b', text)
    excess_caps = len(upper_words) > 6
    return [
        ('Skills section detected', sections['skills']),
        ('Contact info found', sections['contact_info']),
        ('Work experience section detected', sections['experience']),
        ('Education section detected', sections['education']),
        ('Certifications section present', sections['certifications']),
        ('Resume length is reasonable (300-800 words)', 300 <= word_count <= 800),
        ('Not overusing ALL CAPS formatting', not excess_caps),
    ]


def _build_suggestions(keyword_match, content, issues, formatting_checks):
    suggestions = []
    if keyword_match['score'] < 50:
        suggestions.append('Weave in more role-relevant keywords — ATS software scans for exact terms used in job postings.')
    if not content['items'][0][1]:
        suggestions.append('Add numbers to your achievements (%, $, team size, time saved) to make impact concrete.')
    if not content['items'][1][1]:
        suggestions.append('Open bullet points with strong action verbs like "Led", "Built", or "Reduced".')
    if not content['items'][2][1]:
        suggestions.append('Convert long paragraphs into short, scannable bullet points.')
    for label, ok in formatting_checks:
        if not ok and 'ALL CAPS' not in label:
            suggestions.append(f'Add a clear "{label.replace(" detected", "").replace(" found", "").replace(" present", "")}" to your resume.')
    if issues:
        suggestions.append('Clean up the issues flagged above — they\'re the fastest wins for your score.')
    # De-duplicate while preserving order, cap at 6
    seen = set()
    deduped = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            deduped.append(s)
    return deduped[:6]


def _overall_review(score, readability, word_count, sections_found, total_sections, keyword_match, content, issues):
    if score >= 85:
        opening = "This is a strong, ATS-ready resume."
    elif score >= 70:
        opening = "This is a solid resume with a few gaps worth closing."
    elif score >= 50:
        opening = "This resume has a decent foundation but needs some work before it's ATS-ready."
    else:
        opening = "This resume needs meaningful revision to get through most ATS filters."

    strengths = []
    if content['items'][1][1]:
        strengths.append('strong action verbs')
    if content['items'][0][1]:
        strengths.append('quantified achievements')
    if sections_found == total_sections:
        strengths.append('all standard sections present')
    if keyword_match['score'] >= 40:
        strengths.append('good coverage of common industry keywords')

    strength_text = (
        f" It shows {', '.join(strengths)}." if strengths
        else " It's missing most of the elements that make a resume ATS-friendly."
    )

    weakness_text = ""
    if issues:
        weakness_text = f" The main thing holding it back: {issues[0].lower()}"

    return (
        f"{opening}{strength_text}{weakness_text} Overall it scores {score}/100 "
        f"({readability.lower()}), covers {sections_found} of {total_sections} standard sections, "
        f"and runs {word_count} words."
    )


def analyse_resume(text):
    """
    Produce a full ATS-style breakdown - score, keyword match, content
    quality, issues, formatting checks, suggestions and a personalised
    overall review - mirroring the "Resume Analyser" / "ATS Score" panels
    on the homepage.
    """
    text = text or ''
    text_lower = text.lower()
    words = re.findall(r"[A-Za-z']+", text)
    word_count = len(words)

    sections = _find_sections(text_lower)
    sections_found = sum(1 for v in sections.values() if v)
    total_sections = len(sections)

    has_quantified = bool(QUANTIFIED_ACHIEVEMENT_PATTERN.search(text))
    action_verb_hits = sum(1 for v in ACTION_VERBS if re.search(rf'\b{v}\b', text_lower))

    checks = []
    checks.append(('Skills section detected', sections['skills']))
    checks.append(('Contact info found', sections['contact_info']))
    checks.append(('Work experience section detected', sections['experience']))
    checks.append(('Education section detected', sections['education']))
    checks.append(('Quantified achievements found in Experience', has_quantified))
    checks.append(('Certifications section present', sections['certifications']))
    checks.append(('Uses strong action verbs (led, built, improved...)', action_verb_hits >= 3))
    checks.append(('Resume length is reasonable (300-800 words)', 300 <= word_count <= 800))

    passed = sum(1 for _, ok in checks if ok)
    score = round((passed / len(checks)) * 100)

    if score >= 85:
        readability = 'Excellent'
    elif score >= 70:
        readability = 'Good'
    elif score >= 50:
        readability = 'Fair'
    else:
        readability = 'Needs Work'

    keyword_match = _keyword_match(text_lower)
    content_quality = _content_quality(text, text_lower, word_count, has_quantified, action_verb_hits)
    issues = _find_issues(text, text_lower, word_count, content_quality)
    formatting_checks = _formatting_checks(sections, word_count, text)
    suggestions = _build_suggestions(keyword_match, content_quality, issues, formatting_checks)
    overall_review = _overall_review(
        score, readability, word_count, sections_found, total_sections,
        keyword_match, content_quality, issues,
    )

    return {
        'word_count': word_count,
        'sections_found': sections_found,
        'total_sections': total_sections,
        'score': score,
        'readability': readability,
        'checks': checks,
        'sections': sections,
        'keyword_match': keyword_match,
        'content_quality': content_quality,
        'issues': issues,
        'formatting_checks': formatting_checks,
        'suggestions': suggestions,
        'overall_review': overall_review,
    }


# ---------------------------------------------------------------------------
# RESUME <-> JOB DESCRIPTION MATCHING (Resume Optimizer)
# ---------------------------------------------------------------------------

def _keywords(text, min_len=3, top_n=60):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation.replace('+', '').replace('#', '')))
    tokens = [t for t in text.split() if len(t) >= min_len and t not in STOPWORDS]
    freq = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in ranked[:top_n]]


COMMON_MISSPELLINGS = {
    'teh': 'the', 'wich': 'which', 'thier': 'their', 'recieve': 'receive',
    'recieved': 'received', 'recieving': 'receiving', 'acheive': 'achieve',
    'acheived': 'achieved', 'achivement': 'achievement', 'seperate': 'separate',
    'seperated': 'separated', 'definately': 'definitely', 'managment': 'management',
    'experiance': 'experience', 'responsibile': 'responsible', 'responsibilty': 'responsibility',
    'collabration': 'collaboration', 'colaborate': 'collaborate', 'enviroment': 'environment',
    'sucessful': 'successful', 'succesful': 'successful', 'arround': 'around',
    'begining': 'beginning', 'commited': 'committed', 'untill': 'until',
    'occured': 'occurred', 'knowlege': 'knowledge', 'proffesional': 'professional',
    'professionaly': 'professionally', 'excelent': 'excellent', 'oppurtunity': 'opportunity',
    'opportunties': 'opportunities', 'maintainance': 'maintenance', 'strenghten': 'strengthen',
    'developement': 'development', 'developped': 'developed', 'implemantation': 'implementation',
    'anaylsis': 'analysis', 'analize': 'analyze', 'comunication': 'communication',
    'acomplish': 'accomplish', 'accomplishement': 'accomplishment', 'tecnical': 'technical',
    'buisness': 'business', 'calender': 'calendar', 'usefull': 'useful', 'sucess': 'success',
    'writen': 'written', 'creat': 'create', 'liason': 'liaison', 'independant': 'independent',
    'volunter': 'volunteer', 'skilfull': 'skillful', 'inovative': 'innovative',
    'inovation': 'innovation', 'competant': 'competent', 'competance': 'competence',
    'consistant': 'consistent', 'consistancy': 'consistency', 'efficent': 'efficient',
    'efficently': 'efficiently', 'relevent': 'relevant', 'qualifed': 'qualified',
    'univercity': 'university', 'acheivements': 'achievements', 'preformed': 'performed',
    'organiz': 'organize', 'catagory': 'category', 'noticable': 'noticeable',
}

# Lines that look like emails/URLs/handles are left alone by the punctuation
# pass below so fixes never break a real link (e.g. "linkedin.com/in/name").
_URL_OR_EMAIL_LINE = re.compile(
    r'@|https?://|linkedin\.com|github\.com|\b\w+\.(com|org|net|io|in|co|dev)\b',
    re.IGNORECASE,
)


def _fix_spelling_and_punctuation(text):
    """
    Rule-based cleanup pass: corrects a bank of common misspellings, tidies
    spacing around punctuation, capitalises the start of each line, and
    straightens standalone lowercase "i". Contact-style lines (emails,
    URLs) are skipped for the punctuation/capitalisation fixes so a real
    link never gets mangled. Returns (fixed_text, fix_count).
    """
    fixes = 0

    def spelling_repl(m):
        nonlocal fixes
        word = m.group(0)
        corrected = COMMON_MISSPELLINGS.get(word.lower())
        if not corrected:
            return word
        fixes += 1
        return corrected.capitalize() if word[0].isupper() else corrected

    text = re.sub(r"[A-Za-z']+", spelling_repl, text)

    out_lines = []
    for raw_line in text.split('\n'):
        original = raw_line.rstrip()
        line = re.sub(r' {2,}', ' ', original)

        if not _URL_OR_EMAIL_LINE.search(line):
            line = re.sub(r'([,.;:!?])(?=[A-Za-z])', r'\1 ', line)
            line = re.sub(r'\s+([,.;:!?])', r'\1', line)
            line = re.sub(r'\bi\b', 'I', line)
            m = re.search(r'[A-Za-z]', line)
            if m and line[m.start()].islower():
                idx = m.start()
                line = line[:idx] + line[idx].upper() + line[idx + 1:]

        if line != original:
            fixes += 1
        out_lines.append(line)

    return '\n'.join(out_lines), fixes


_CASUAL_TO_PROFESSIONAL = [
    (r'\bworked on\b', 'developed'),
    (r'\bhelped (?:with|to)\b', 'contributed to'),
    (r'\bdid\b', 'performed'),
    (r'\bmade\b', 'created'),
    (r'\bgot\b', 'obtained'),
    (r'\bstuff\b', 'tasks'),
    (r'\bthings\b', 'tasks'),
    (r'\ba lot of\b', 'substantial'),
    (r'\btalked to\b', 'liaised with'),
    (r'\bdealt with\b', 'managed'),
    (r'\blooked after\b', 'oversaw'),
    (r'\bfixed bugs\b', 'resolved software defects'),
    (r'\bkept track of\b', 'monitored'),
]


def _professionalize_text(text):
    """
    Swap common casual/conversational phrasing for professional resume
    language (e.g. "worked on" -> "developed"), preserving the case of the
    first letter of whatever was matched. Returns (new_text, rewrite_count).
    """
    rewrites = 0

    def make_repl(replacement):
        def repl(m):
            nonlocal rewrites
            rewrites += 1
            matched = m.group(0)
            return replacement[0].upper() + replacement[1:] if matched[0].isupper() else replacement
        return repl

    for pattern, replacement in _CASUAL_TO_PROFESSIONAL:
        text = re.sub(pattern, make_repl(replacement), text, flags=re.IGNORECASE)

    return text, rewrites


_WEAK_OPENER_VERBS = [
    (r'^(?:was |is |been )?worked on\s+', 'Developed'),
    (r'^helped (?:with |to )?', 'Contributed to'),
    (r'^(?:was |is |been )?responsible for\s+', 'Managed'),
    (r'^(?:was |is |been )?in charge of\s+', 'Led'),
    (r'^assisted with\s+', 'Supported'),
    (r'^(?:was |is |been )?tasked with\s+', 'Handled'),
    (r'^dealt with\s+', 'Managed'),
    (r'^was part of\s+', 'Collaborated on'),
    (r'^(?:was |is |been )?part of the team that\s+', 'Collaborated with the team to'),
    (r'^did\s+', 'Completed'),
]


def _strengthen_bullet(bullet):
    """
    Rewrite a weak-opener achievement line ("Worked on...", "Helped
    with...") using a strong action verb, keeping every specific the
    person actually wrote intact — nothing about what they did is
    invented. Also flags short, number-free bullets so the person knows
    to add a concrete tool/tech name or metric themselves, e.g. turning
    "Worked on a college website" into "Developed a college website" and
    suggesting they name the stack and impact for the strongest version.
    Returns (new_text, changed, needs_detail).
    """
    original = bullet.strip()
    if not original:
        return original, False, False

    changed = False
    new_text = original

    for pattern, verb in _WEAK_OPENER_VERBS:
        if re.match(pattern, original, re.IGNORECASE):
            rest = re.sub(pattern, '', original, count=1, flags=re.IGNORECASE).strip()
            rest = re.sub(r'^(a|an|the)\s+', '', rest, flags=re.IGNORECASE)
            if rest:
                new_text = f'{verb} {rest}'
                changed = True
            break

    if changed:
        new_text = new_text[0].upper() + new_text[1:]

    has_number = bool(QUANTIFIED_ACHIEVEMENT_PATTERN.search(original))
    needs_detail = (not has_number) and len(original.split()) <= 8

    return new_text, changed, needs_detail


def _section_optimization_tips(sections_found, target_job_title):
    """One tailored tip per standard resume section, based on whether
    ResumeIQ can actually find that section in the uploaded file."""
    role = target_job_title or 'the role you want'

    tips = [
        {
            'section': 'Contact Info',
            'ok': sections_found['contact_info'],
            'tip': (
                'Found — double-check the email, phone number and LinkedIn URL are current and on their own line.'
                if sections_found['contact_info'] else
                'Not clearly detected. Add a line with your email, phone number and LinkedIn URL near the top.'
            ),
        },
        {
            'section': 'Summary',
            'ok': sections_found['summary'],
            'tip': (
                f'Found — make sure it names "{role}" and your top 2-3 strengths in 2-4 sentences.'
                if sections_found['summary'] else
                f'Not found. Add a short 2-4 sentence summary opening with "{role}" and your strongest, most relevant skills.'
            ),
        },
        {
            'section': 'Skills',
            'ok': sections_found['skills'],
            'tip': (
                'Found — list them as a scannable, comma-separated line and match the exact terms used in job postings.'
                if sections_found['skills'] else
                'Not found. Add a dedicated Skills section — ATS software scans for exact keyword matches here.'
            ),
        },
        {
            'section': 'Experience',
            'ok': sections_found['experience'],
            'tip': (
                'Found — open every bullet with a strong action verb and add a number (%, $, team size, time saved) wherever you can.'
                if sections_found['experience'] else
                'Not found. Add a Work Experience section with bullet points describing what you did and its impact.'
            ),
        },
        {
            'section': 'Education',
            'ok': sections_found['education'],
            'tip': (
                'Found — list degree, institution and graduation year, in that order.'
                if sections_found['education'] else
                'Not found. Add your degree, institution and graduation year.'
            ),
        },
        {
            'section': 'Certifications',
            'ok': sections_found['certifications'],
            'tip': (
                'Found — nice, this adds credibility and extra keyword coverage.'
                if sections_found['certifications'] else
                'None found. If you have any relevant certifications or courses, add them — an easy win for keyword coverage.'
            ),
        },
    ]
    return tips


BULLET_MARKER_PATTERN = re.compile(r'^(\s*[-•*▪●]\s+)(.*)$')

_HEADER_WORDS = {
    'summary', 'objective', 'profile', 'about', 'about me', 'skills',
    'technical skills', 'core competencies', 'competencies', 'experience',
    'work experience', 'employment history', 'professional experience',
    'education', 'academic background', 'certifications', 'certificates',
    'licenses', 'projects', 'personal projects', 'academic projects',
    'achievements', 'accomplishments', 'awards', 'honors', 'languages',
    'hobbies', 'interests', 'hobbies & interests', 'references',
    'volunteer experience', 'volunteering', 'extracurricular', 'activities',
    'publications', 'contact', 'contact information', 'personal details',
    'declaration',
}


def _looks_like_heading(line):
    """A line counts as a section heading if it's short, isn't a bullet or
    a contact/URL line, and either reads as ALL CAPS or matches a common
    resume section name — used to turn the flat optimized text into a
    printable, Resume-Creator-style page."""
    stripped = line.strip().rstrip(':').strip()
    if not stripped or len(stripped) > 40:
        return False
    if BULLET_MARKER_PATTERN.match(line):
        return False
    if '@' in stripped or re.search(r'https?://|www\.', stripped, re.IGNORECASE):
        return False
    letters = re.sub(r'[^A-Za-z]', '', stripped)
    if not letters:
        return False
    if stripped.isupper() and len(letters) >= 3:
        return True
    return stripped.lower() in _HEADER_WORDS


def _group_items(items):
    """Collapse consecutive bullet/text items into runs, so the template
    can wrap consecutive bullets in one <ul> instead of one per line."""
    runs = []
    for item in items:
        if runs and runs[-1]['type'] == item['type']:
            runs[-1]['items'].append(item['content'])
        else:
            runs.append({'type': item['type'], 'items': [item['content']]})
    return runs


def _build_print_sections(text):
    """
    Turn the optimized resume text into the same shape the Resume
    Creator's preview uses — an optional name/contact header (whatever
    came before the first detected heading) followed by heading +
    bullet/paragraph sections — so it can be rendered as a clean page and
    downloaded as an actual PDF via the browser's print dialog, instead of
    a plain .txt dump.
    """
    raw_lines = [ln.strip() for ln in text.split('\n') if ln.strip()]

    idx = 0
    header_lines = []
    while idx < len(raw_lines) and not _looks_like_heading(raw_lines[idx]):
        header_lines.append(raw_lines[idx])
        idx += 1

    header = None
    if header_lines:
        header = {'name': header_lines[0], 'contact_lines': header_lines[1:]}

    sections = []
    current = None
    for line in raw_lines[idx:]:
        if _looks_like_heading(line):
            current = {'heading': line.rstrip(':').strip(), 'items': []}
            sections.append(current)
            continue
        if current is None:
            current = {'heading': None, 'items': []}
            sections.append(current)
        marker_match = BULLET_MARKER_PATTERN.match(line)
        if marker_match:
            current['items'].append({'type': 'bullet', 'content': marker_match.group(2).strip()})
        else:
            current['items'].append({'type': 'text', 'content': line})

    for section in sections:
        section['runs'] = _group_items(section.pop('items'))

    return {'header': header, 'sections': sections}


def _serialize_print_sections(print_sections):
    """Flatten the header + heading/runs structure back into plain resume
    text — used after the summary step (below) edits that structure, so
    every other pass (ATS checklist, keyword match, the copyable text)
    sees the fully updated resume, not the pre-summary version."""
    lines = []
    header = print_sections.get('header')
    if header:
        lines.append(header['name'])
        lines.extend(header.get('contact_lines', []))
        lines.append('')

    for section in print_sections['sections']:
        if section.get('heading'):
            lines.append(section['heading'].upper())
        for run in section['runs']:
            if run['type'] == 'bullet':
                lines.extend(f'- {item}' for item in run['items'])
            else:
                lines.extend(run['items'])
        lines.append('')

    return '\n'.join(lines).strip() + '\n'


def _extract_skills_from_sections(print_sections):
    """Pull the person's own listed skills out of their Skills section, so
    the generated/enhanced summary can reference real skills instead of
    inventing any."""
    for section in print_sections['sections']:
        if 'skill' in (section.get('heading') or '').lower():
            skills = []
            for run in section['runs']:
                for item in run['items']:
                    skills.extend(p.strip() for p in re.split(r'[,;|•·]', item) if p.strip())
            return skills[:8]
    return []


_LEVEL_LEAD = {
    'student': 'Motivated student and aspiring',
    'entry': 'Detail-oriented, early-career',
    'mid': 'Experienced',
    'senior': 'Accomplished, senior-level',
    'leadership': 'Results-driven leader and',
}


def _generate_summary_sentence(target_job_title, target_industry, experience_level, skills):
    lead = _LEVEL_LEAD.get(experience_level, 'Motivated')
    role = (target_job_title or 'professional').strip()
    sentence = f'{lead} {role.lower()}'
    if target_industry.strip():
        sentence += f' targeting {target_industry.strip()} roles'
    if skills:
        sentence += f', with hands-on experience in {", ".join(skills[:4])}'
    sentence += '.'
    return sentence[0].upper() + sentence[1:]


def _apply_summary_optimization(print_sections, target_job_title, target_industry, experience_level):
    """
    Make sure the resume's Summary actively targets the role the person
    typed in: if a Summary/Objective exists but doesn't mention the
    target job title, a tailored lead sentence is added in front of it.
    If there's no Summary at all, one is generated from the target
    role/industry the person entered plus the skills already listed on
    their own resume — nothing about their experience is invented, only
    their own inputs are used. Mutates `print_sections` in place and
    returns a short description of what it did, or None if nothing changed.
    """
    role = (target_job_title or '').strip()
    if not role:
        return None

    skills = _extract_skills_from_sections(print_sections)

    for section in print_sections['sections']:
        heading = (section.get('heading') or '').lower()
        if heading in ('summary', 'objective', 'profile', 'about', 'about me'):
            existing_text = ' '.join(
                item for run in section['runs'] if run['type'] == 'text' for item in run['items']
            )
            if role.lower() in existing_text.lower():
                return None
            sentence = _generate_summary_sentence(target_job_title, target_industry, experience_level, skills)
            section['runs'].insert(0, {'type': 'text', 'items': [sentence]})
            return f'Added a lead sentence to your {section["heading"]} targeting "{role}".'

    sentence = _generate_summary_sentence(target_job_title, target_industry, experience_level, skills)
    print_sections['sections'].insert(0, {
        'heading': 'Summary',
        'runs': [{'type': 'text', 'items': [sentence]}],
    })
    return f'Generated a new Summary section targeting "{role}" from your own listed skills.'


def optimize_resume_full(resume_text, target_job_title, job_description='', target_industry='', experience_level=''):
    """
    The full "AI Optimize" pass behind the Resume Optimizer tool. In order:
    fixes spelling and punctuation, rewrites casual phrasing into
    professional language, strengthens weak achievement bullets, checks
    ATS formatting section-by-section, and scores keyword coverage against
    the pasted job description (or, if none was given, against a keyword
    set built from the target job title/industry). Returns everything the
    template needs, including a ready-to-copy `final_resume` string.
    Rule-based and fully local, like the rest of this file — nothing about
    the person's real experience, employers, dates or numbers is invented,
    only wording and formatting are improved.
    """
    resume_text = resume_text or ''
    job_description = job_description or ''

    # 1) Spelling + punctuation.
    fixed_text, spelling_fixes = _fix_spelling_and_punctuation(resume_text)

    # 2) Casual -> professional phrasing.
    professional_text, phrasing_rewrites = _professionalize_text(fixed_text)

    # 3) Strengthen weak achievement bullets, line by line. "True original"
    #    is read from *before* the professionalize pass, so the before/after
    #    comparison shown to the person reflects everything that changed —
    #    including phrase swaps that already happened in step 2 above.
    fixed_lines = fixed_text.split('\n')
    lines = professional_text.split('\n')
    bullet_improvements = []
    for i, line in enumerate(lines):
        marker_match = BULLET_MARKER_PATTERN.match(line)
        if not marker_match:
            continue
        marker, content = marker_match.group(1), marker_match.group(2)
        if not content.strip():
            continue

        true_original_match = BULLET_MARKER_PATTERN.match(fixed_lines[i]) if i < len(fixed_lines) else None
        true_original = true_original_match.group(2).strip() if true_original_match else content.strip()

        strengthened, verb_swapped, needs_detail = _strengthen_bullet(content)
        final_content = strengthened if verb_swapped else content.strip()
        changed = final_content.strip().lower() != true_original.lower()

        if changed:
            lines[i] = f'{marker}{final_content}'
        if changed or needs_detail:
            bullet_improvements.append({
                'original': true_original,
                'improved': final_content if changed else None,
                'needs_detail': needs_detail,
            })
    final_resume = '\n'.join(lines)

    # 4) Build the section structure, then make sure the Summary actually
    #    targets the role the person told us they want — this is the step
    #    that uses the Target Job Title / Industry / Experience Level
    #    inputs directly, and it's re-serialized back into `final_resume`
    #    so every check below (and the copyable text) reflects it too.
    print_sections = _build_print_sections(final_resume)
    summary_change = _apply_summary_optimization(print_sections, target_job_title, target_industry, experience_level)
    final_resume = _serialize_print_sections(print_sections)

    # 5) Section detection + per-section tips (run on the now-updated text,
    #    so a freshly-added Summary is correctly picked up).
    text_lower = final_resume.lower()
    sections_found = _find_sections(text_lower)
    section_tips = _section_optimization_tips(sections_found, target_job_title)

    # 6) ATS formatting checklist + score.
    word_count = len(re.findall(r"[A-Za-z']+", final_resume))
    ats_checks = _formatting_checks(sections_found, word_count, final_resume)
    ats_score = round((sum(1 for _, ok in ats_checks if ok) / len(ats_checks)) * 100)

    # 7) Keyword match — against the pasted job description if given,
    #    otherwise against a keyword set built from the target role/industry.
    resume_words = set(_keywords(final_resume, top_n=1000))
    if job_description.strip():
        target_keywords = _keywords(job_description, top_n=40)
        keyword_source = 'job description'
    else:
        role_terms = _keywords(f'{target_job_title} {target_industry}', min_len=3, top_n=10)
        target_keywords = list(dict.fromkeys(role_terms + COMMON_ATS_KEYWORDS))[:40]
        keyword_source = 'target role'

    matched = [kw for kw in target_keywords if kw in resume_words]
    missing = [kw for kw in target_keywords if kw not in resume_words]
    match_score = round((len(matched) / len(target_keywords)) * 100) if target_keywords else 0

    # 8) A plain-English list of exactly what was changed, for the person
    #    to point to (e.g. when showing this to a teacher) — not just a
    #    score, but a record of the actual edits made.
    changes_summary = []
    if spelling_fixes:
        changes_summary.append(f'Fixed {spelling_fixes} spelling/punctuation issue{"s" if spelling_fixes != 1 else ""}.')
    if phrasing_rewrites:
        changes_summary.append(f'Rewrote {phrasing_rewrites} casual phrase{"s" if phrasing_rewrites != 1 else ""} into more professional language.')
    changed_bullets = sum(1 for b in bullet_improvements if b['improved'])
    if changed_bullets:
        changes_summary.append(f'Strengthened {changed_bullets} achievement bullet{"s" if changed_bullets != 1 else ""} with a stronger opening verb.')
    if summary_change:
        changes_summary.append(summary_change)
    if not changes_summary:
        changes_summary.append(
            "Your wording and formatting were already solid, so the main improvements are the keyword and "
            "section suggestions below rather than rewritten text."
        )

    return {
        'target_job_title': target_job_title,
        'target_industry': target_industry,
        'experience_level': experience_level,
        'spelling_fixes': spelling_fixes,
        'phrasing_rewrites': phrasing_rewrites,
        'bullet_improvements': bullet_improvements,
        'summary_change': summary_change,
        'changes_summary': changes_summary,
        'section_tips': section_tips,
        'ats_checks': ats_checks,
        'ats_score': ats_score,
        'match_score': match_score,
        'matched': matched,
        'missing': missing,
        'keyword_source': keyword_source,
        'keyword_count': len(target_keywords),
        'final_resume': final_resume,
        'print_sections': print_sections,
        'original_resume': resume_text,
    }


# ---------------------------------------------------------------------------
# RESUME CREATOR
# ---------------------------------------------------------------------------

def build_resume_context(form_data):
    """Turn cleaned form data into a structured context for the resume template."""
    experience_entries = []
    titles = form_data.getlist('exp_title')
    companies = form_data.getlist('exp_company')
    durations = form_data.getlist('exp_duration')
    bullets = form_data.getlist('exp_bullets')

    for title, company, duration, bullet_block in zip(titles, companies, durations, bullets):
        if not (title or company):
            continue
        experience_entries.append({
            'title': title,
            'company': company,
            'duration': duration,
            'bullets': [b.strip('-• ').strip() for b in bullet_block.splitlines() if b.strip()],
        })

    education_entries = []
    schools = form_data.getlist('edu_school')
    degrees = form_data.getlist('edu_degree')
    years = form_data.getlist('edu_year')
    for school, degree, year in zip(schools, degrees, years):
        if not (school or degree):
            continue
        education_entries.append({'school': school, 'degree': degree, 'year': year})

    project_entries = []
    proj_titles = form_data.getlist('project_title')
    proj_tech = form_data.getlist('project_tech')
    proj_desc = form_data.getlist('project_desc')
    for p_title, p_tech, p_desc in zip(proj_titles, proj_tech, proj_desc):
        if not p_title:
            continue
        project_entries.append({
            'title': p_title,
            'tech': [t.strip() for t in p_tech.split(',') if t.strip()],
            'description': p_desc.strip(),
        })

    skills = [s.strip() for s in form_data.get('skills', '').split(',') if s.strip()]

    context = {
        'full_name': form_data.get('full_name', '').strip(),
        'job_title': form_data.get('job_title', '').strip(),
        'email': form_data.get('email', '').strip(),
        'phone': form_data.get('phone', '').strip(),
        'location': form_data.get('location', '').strip(),
        'linkedin': form_data.get('linkedin', '').strip(),
        'summary': form_data.get('summary', '').strip(),
        'skills': skills,
        'experience': experience_entries,
        'education': education_entries,
        'projects': project_entries,
        'certifications': [c.strip() for c in form_data.get('certifications', '').split(',') if c.strip()],
        'achievements': [a.strip() for a in form_data.get('achievements', '').split(',') if a.strip()],
        'languages': [l.strip() for l in form_data.get('languages', '').split(',') if l.strip()],
        'hobbies': [h.strip() for h in form_data.get('hobbies', '').split(',') if h.strip()],
        'activities': [a.strip('-• ').strip() for a in form_data.get('activities', '').splitlines() if a.strip()],
        'personal_details': {
            'dob': form_data.get('dob', '').strip(),
            'gender': form_data.get('gender', '').strip(),
            'nationality': form_data.get('nationality', '').strip(),
            'marital_status': form_data.get('marital_status', '').strip(),
        },
        'include_references': bool(form_data.get('include_references')),
        'include_declaration': bool(form_data.get('include_declaration')),
        'declaration_place': form_data.get('declaration_place', '').strip(),
    }

    return enrich_resume_context(context)


# ---------------------------------------------------------------------------
# RESUME CREATOR — auto-enrichment ("AI Boost")
#
# Rule-based text generation that turns sparse form input into a fuller,
# more polished resume. Important: this only expands/rephrases what the
# user actually typed (job titles, skills, company names, etc.) — it never
# invents employers, dates, degrees, or fake quantified stats that aren't
# backed by something the user entered, since that would misrepresent the
# person to a real employer. Generic professional phrasing and universal
# soft-skill lines are fair game (every resume template uses these);
# specific fabricated facts are not.
# ---------------------------------------------------------------------------

_GENERIC_STRENGTHS = [
    'Strong problem-solving and analytical thinking',
    'Fast learner, quick to pick up new tools and technologies',
    'Clear communicator who works well in team settings',
    'Detail-oriented with a focus on quality',
    'Reliable under deadlines and shifting priorities',
    'Collaborative mindset with a proactive, self-starter attitude',
    'Comfortable balancing multiple tasks at once',
    'Genuine enthusiasm for learning and taking on new challenges',
]

_ROLE_BULLET_BANK = {
    'developer': [
        'Wrote clean, maintainable code for {focus} following industry best practices',
        'Debugged and resolved issues across {focus}, improving overall stability',
        'Collaborated with the wider team to plan, build, and ship features on schedule',
        'Participated in code reviews and testing to keep quality high',
        'Picked up new frameworks and tools quickly to meet project needs',
    ],
    'engineer': [
        'Designed and implemented solutions for {focus}, focusing on reliability and performance',
        'Worked cross-functionally to translate requirements into working systems',
        'Documented technical decisions to keep the codebase easy to maintain',
        'Contributed to planning and estimation for upcoming feature work',
        'Troubleshot issues methodically, tracing root causes before proposing fixes',
    ],
    'manager': [
        'Coordinated day-to-day activities to keep the team aligned on priorities',
        'Supported team members with guidance, feedback, and clear direction',
        'Worked with stakeholders to keep projects on track and within scope',
        'Helped streamline processes to improve overall team efficiency',
        'Kept clear, consistent communication flowing between teams',
    ],
    'designer': [
        'Created user-focused designs for {focus}, balancing usability and visual appeal',
        'Worked closely with developers to bring designs to life accurately',
        'Iterated on designs based on feedback and usability considerations',
        'Maintained consistency across the design system and brand guidelines',
        'Researched design patterns to keep work aligned with best practices',
    ],
    'analyst': [
        'Analysed data related to {focus} to support informed decision-making',
        'Prepared clear, concise reports and summaries for stakeholders',
        'Identified trends and opportunities for process improvement',
        'Maintained accuracy and consistency across data sources',
        'Worked with cross-functional teams to turn findings into action',
    ],
    'marketing': [
        'Supported campaigns and initiatives related to {focus}',
        'Coordinated with the team to plan and execute marketing activities',
        'Tracked performance and shared insights to guide future strategy',
        'Helped maintain consistent messaging across channels',
        'Assisted with content creation and scheduling across platforms',
    ],
    'sales': [
        'Built and maintained relationships with clients and prospects',
        'Supported the sales process from outreach through to close',
        'Worked with the team to meet targets and improve conversion',
        'Kept accurate records of leads, opportunities, and follow-ups',
        'Followed up promptly to keep prospects engaged through the pipeline',
    ],
    'support': [
        'Responded to and resolved queries related to {focus} in a timely manner',
        'Maintained clear documentation for common issues and resolutions',
        'Worked with the team to improve overall response quality',
        'Kept a positive, solution-focused approach when handling requests',
        'Escalated complex issues appropriately while keeping users informed',
    ],
    'intern': [
        'Assisted the team with day-to-day tasks related to {focus}',
        'Learned and applied new tools and processes quickly',
        'Contributed ideas and support during team discussions and planning',
        'Took initiative on small tasks and saw them through to completion',
        'Shadowed senior team members to build practical, hands-on skills',
    ],
    'default': [
        'Handled core responsibilities related to {focus} reliably and on time',
        'Worked closely with the team to support shared goals',
        'Took initiative to improve day-to-day processes where possible',
        'Adapted quickly to new tasks and changing priorities',
        'Built a solid working knowledge of the tools and systems involved',
    ],
}

_SUMMARY_TEMPLATES = [
    "{article} {role} with hands-on experience in {skills}. Known for {trait} and a strong focus on delivering reliable, high-quality work.",
    "Motivated {role} skilled in {skills}. Brings {trait} and a genuine drive to keep learning and improving.",
    "Detail-oriented {role} with a solid foundation in {skills}. Comfortable working in team settings and known for {trait}.",
    "{article} {role} who combines {skills} with {trait}, always looking to take on new challenges and grow professionally.",
]

_TRAITS = [
    'strong problem-solving skills', 'clear communication', 'a proactive, self-starter attitude',
    'attention to detail', 'the ability to learn quickly', 'a collaborative team-first mindset',
]


def _rng_for(seed_text):
    return random.Random(seed_text or 'resumeiq-default')


def _article_for(word):
    return 'An' if word[:1].lower() in 'aeiou' else 'A'


def _role_bucket(job_title):
    jt = (job_title or '').lower()
    for key in ('intern', 'manager', 'lead', 'engineer', 'developer', 'designer',
                'analyst', 'marketing', 'sales', 'support'):
        if key in jt:
            return 'manager' if key == 'lead' else key
    return 'default'


def _polish_bullet(bullet):
    """Tidy a user-typed bullet: capitalize, ensure it opens with an action verb."""
    text = bullet.strip().strip('.').strip()
    if not text:
        return text

    first_word = re.match(r"[A-Za-z']+", text)
    starts_with_verb = bool(first_word and first_word.group(0).lower() in ACTION_VERBS)

    if not starts_with_verb:
        rng = _rng_for(text)
        verb = rng.choice(['Contributed to', 'Handled', 'Supported', 'Worked on'])
        text = f"{verb} {text[0].lower()}{text[1:]}" if len(text) > 1 else f"{verb} {text}"

    return text[0].upper() + text[1:]


def _generate_bullets_for(entry, skills):
    """Produce up to 4 sensible default bullets for an experience entry."""
    bucket = _role_bucket(entry.get('title', ''))
    bank = _ROLE_BULLET_BANK.get(bucket, _ROLE_BULLET_BANK['default'])
    focus = entry.get('company') or (skills[0] if skills else 'core projects')

    rng = _rng_for((entry.get('title') or '') + (entry.get('company') or ''))
    picks = bank[:]
    rng.shuffle(picks)
    return [p.format(focus=focus) for p in picks[:4]]


def _generate_summary(full_name, job_title, skills, has_experience):
    role = job_title or 'professional'
    skill_list = skills[:3] if skills else ['problem-solving', 'teamwork', 'adaptability']
    skills_text = ', '.join(skill_list[:-1]) + (f' and {skill_list[-1]}' if len(skill_list) > 1 else skill_list[0])

    rng = _rng_for(full_name + role)
    template = rng.choice(_SUMMARY_TEMPLATES)
    trait = rng.choice(_TRAITS)

    return template.format(article=_article_for(role), role=role, skills=skills_text, trait=trait)


def enrich_resume_context(ctx):
    """
    "AI Boost" pass: fills in a professional summary if left blank, expands
    thin/empty experience bullets into fuller ones, tidies existing bullets,
    tops up a short skills list with a couple of universal ones, and adds a
    generated Key Strengths section when the resume otherwise looks sparse —
    all aimed at producing a full one-page resume even from minimal input.
    Never invents employers, dates, degrees or fake numbers.
    """
    skills = list(ctx.get('skills') or [])
    experience = ctx.get('experience') or []
    projects = ctx.get('projects') or []
    education = ctx.get('education') or []

    # 1) Expand / polish experience bullets. Anything the user typed is kept
    #    (just tidied up); every entry is topped up to 4 bullets so no job
    #    entry looks bare on the page.
    for entry in experience:
        existing = [_polish_bullet(b) for b in (entry.get('bullets') or []) if b.strip()]
        if len(existing) < 4:
            generated = _generate_bullets_for(entry, skills)
            for g in generated:
                if len(existing) >= 4:
                    break
                if g not in existing:
                    existing.append(g)
        entry['bullets'] = existing

    # 2) Auto-generate a summary if the user left it blank.
    if not ctx.get('summary'):
        ctx['summary'] = _generate_summary(
            ctx.get('full_name', ''), ctx.get('job_title', ''), skills, bool(experience)
        )

    # 3) Top up a thin skills list with a couple of universal, honest additions
    #    (never claims to be technical skills the person didn't list).
    if len(skills) < 6:
        rng = _rng_for(ctx.get('full_name', ''))
        pool = ['Communication', 'Teamwork', 'Time Management', 'Adaptability',
                'Problem Solving', 'Attention to Detail']
        needed = min(len(pool), 6 - len(skills))
        for extra in rng.sample(pool, k=needed):
            if extra not in skills:
                skills.append(extra)
    ctx['skills'] = skills

    # 4) Key Strengths section: shown whenever the resume's core content
    #    (experience + projects + education) is on the light side, so the
    #    page still reads as full rather than trailing off with blank space.
    #    Plain, honest, non-fabricated statements only.
    content_blocks = len(experience) + len(projects) + len(education)
    if content_blocks <= 2:
        rng = _rng_for(ctx.get('full_name', '') + 'strengths')
        ctx['strengths'] = rng.sample(_GENERIC_STRENGTHS, k=len(_GENERIC_STRENGTHS))
    else:
        ctx['strengths'] = []

    # 5) Rough total-experience estimate from duration strings, for display
    #    only if it can be computed confidently from years the user gave.
    all_years = []
    for entry in experience:
        all_years += [int(y) for y in re.findall(r'\b((?:19|20)\d{2})\b', entry.get('duration', ''))]
    if len(all_years) >= 2:
        span = max(all_years) - min(all_years)
        ctx['years_experience'] = span if 0 < span <= 50 else None
    else:
        ctx['years_experience'] = None

    # 6) Declaration block (standard closing statement on Indian resumes) —
    #    only added if the user opted in; text is a fixed, honest boilerplate
    #    plus the place/name/date they gave, never fabricated content.
    if ctx.get('include_declaration'):
        ctx['declaration_text'] = (
            'I hereby declare that the information provided above is true and '
            'accurate to the best of my knowledge.'
        )
    else:
        ctx['declaration_text'] = ''

    return ctx


# ---------------------------------------------------------------------------
# Chat Bot — plain-Python, keyword-matched Q&A engine. Covers resumes, job
# search, study habits, and interview prep across dozens of sub-topics.
# Matching is typo-tolerant (edit-distance based) so small spelling
# mistakes still find the right answer. No external AI service is called —
# everything is matched locally against the user's message.
# ---------------------------------------------------------------------------
_CHATBOT_RULES = [
    (
        ['hello', 'hi', 'hey', 'yo', 'sup', 'greetings'],
        [
            "Hey! I'm the ResumeIQ assistant. Ask me anything about resumes, job hunting, studying, or interviews.",
            "Hi there! Happy to help with resume tips, job search strategy, study habits, or interview prep — what's on your mind?",
        ],
    ),
    (
        ['how are you', 'whats up', "what's up"],
        [
            "Running smoothly and ready to help! What do you want to know about resumes, jobs, studying, or interviews?",
        ],
    ),
    (
        ['bye', 'goodbye', 'see you', 'cya'],
        [
            "Good luck out there — come back anytime you need resume, job, study, or interview help!",
        ],
    ),
    (
        ['thank', 'thanks', 'thx', 'appreciate'],
        [
            "Anytime! Good luck out there.",
            "You're welcome — feel free to ask me anything else.",
        ],
    ),
    (
        ['ats', 'applicant tracking'],
        [
            "ATS software scans your resume for keywords from the job description before a human ever sees it. Stick to standard section headings (Experience, Education, Skills), avoid text inside images or tables, use a simple single-column layout, and mirror the exact wording the posting uses for your skills. Our Resume Analyser will score this for you directly.",
        ],
    ),
    (
        ['resume format', 'resume layout', 'resume design', 'resume template'],
        [
            "Stick to a clean, single-column layout with clear section headings — reverse-chronological order (most recent first) is the safest default. Avoid tables, columns, headers/footers, and graphics, since they often confuse ATS parsers even if they look nice to a human.",
        ],
    ),
    (
        ['resume length', 'how long should my resume', 'one page resume', 'two page resume'],
        [
            "One page is the standard for students, fresh graduates, and anyone with under ~8 years of experience. Two pages is fine once you have substantial experience to show — but never pad it just to fill space.",
        ],
    ),
    (
        ['resume summary', 'career objective', 'resume objective', 'professional summary'],
        [
            "A resume summary should be 2-3 sentences at the top stating your role, years of experience (or relevant coursework/projects if you're a student), and your strongest achievement or skill. Skip generic objective statements like 'seeking a challenging position' — they waste space without saying anything specific.",
        ],
    ),
    (
        ['action verb', 'bullet point', 'resume bullet', 'how to write resume points'],
        [
            "Start every bullet with a strong action verb (Led, Built, Reduced, Launched, Automated) and follow the formula: verb + what you did + measurable result. 'Automated a manual report, saving 5 hours a week' is far stronger than 'Responsible for reports'.",
        ],
    ),
    (
        ['resume mistake', 'resume error', 'common resume mistakes'],
        [
            "The most common resume mistakes: typos/grammar errors, generic bullet points with no numbers, an unclear job title, listing duties instead of achievements, and a font/formatting mess an ATS can't read. Running it through our Resume Analyser catches most of these instantly.",
        ],
    ),
    (
        ['resume gap', 'employment gap', 'gap in resume'],
        [
            "A gap isn't disqualifying — briefly and honestly explain it in your cover letter or interview (studying, caregiving, health, layoffs are all normal), and fill the resume gap itself with anything productive you did: freelance work, courses, volunteering, or personal projects.",
        ],
    ),
    (
        ['resume', 'cv', 'curriculum vitae'],
        [
            "For a strong resume: lead each bullet with an action verb, quantify results wherever possible (numbers, %, $), keep it to one page for under ~8 years of experience, and tailor the skills section to the job description. Try the Resume Creator if you're starting from scratch, or the Resume Analyser if you already have one.",
            "A resume should tell a hiring manager what you achieved, not just what you did — 'Reduced onboarding time by 30% by rebuilding the training doc' beats 'Responsible for onboarding.' Want tips on a specific section?",
        ],
    ),
    (
        ['cover letter'],
        [
            "Keep your cover letter to 3-4 short paragraphs: why this role, one or two concrete achievements that match what they're asking for, and why you specifically want this company. Avoid repeating your resume line-by-line — use it to add context numbers can't show.",
        ],
    ),
    (
        ['portfolio', 'github profile', 'personal website'],
        [
            "A portfolio matters most for design, dev, and writing roles — show 3-4 of your best projects with a short write-up of the problem, your role, and the outcome, rather than dumping everything you've ever made. Link it clearly from your resume and LinkedIn.",
        ],
    ),
    (
        ['reference', 'references'],
        [
            "You don't need to write 'References available upon request' anymore — it's assumed. Instead, prepare 2-3 people (a manager, professor, or mentor) who know your work well, and give them a heads-up before you list their contact info anywhere.",
        ],
    ),
    (
        ['interview question', 'tell me about yourself'],
        [
            "For 'tell me about yourself', use a short present-past-future structure: what you do now, one relevant highlight from your background, then why you want this specific role. Keep it under 90 seconds — it's an opener, not your whole life story.",
        ],
    ),
    (
        ['strength', 'weakness'],
        [
            "For strengths, pick one that's actually relevant to the role and back it with a quick example. For weaknesses, pick something real but not disqualifying, and show what you're actively doing to improve it — that's what interviewers are really listening for.",
        ],
    ),
    (
        ['why should we hire you', 'why should i hire you'],
        [
            "Connect 2-3 of your strongest, most relevant skills directly to what the job actually needs, back each with a quick concrete result, and close by showing genuine interest in the company's mission — specific beats impressive-sounding every time.",
        ],
    ),
    (
        ['star method', 'behavioral interview', 'behavioural interview'],
        [
            "The STAR method structures answers to 'tell me about a time...' questions: Situation (brief context), Task (what you needed to do), Action (what you specifically did), Result (the measurable outcome). Prepare 3-4 stories in advance and adapt them to whatever's asked.",
        ],
    ),
    (
        ['phone interview', 'video interview', 'virtual interview', 'zoom interview'],
        [
            "For phone/video interviews: test your camera, mic, and internet beforehand, keep notes just off-screen (not cheating — totally normal), look at the camera lens rather than the screen when talking, and treat it with the same prep and energy as an in-person interview.",
        ],
    ),
    (
        ['panel interview', 'group interview'],
        [
            "In a panel or group interview, make eye contact with whoever asked the question but glance at the others occasionally, address each panelist by name if you catch it, and in group settings, listen actively and build on others' points rather than only pushing your own.",
        ],
    ),
    (
        ['dress code', 'what to wear', 'interview attire', 'interview outfit'],
        [
            "When in doubt, dress one notch more formal than the company's everyday style — business casual is a safe default for most interviews. It matters less than your answers, but it's an easy way to remove one source of nerves.",
        ],
    ),
    (
        ['body language', 'eye contact', 'nervous habits'],
        [
            "Sit up, keep your hands visible and relaxed, make natural eye contact (not a stare-down), and nod occasionally to show you're engaged. A firm handshake and a genuine smile at the start go a long way before you've even said anything.",
        ],
    ),
    (
        ['follow up email', 'thank you email', 'thank you note'],
        [
            "Send a short thank-you email within 24 hours of the interview: thank them for their time, mention one specific thing you discussed, and reaffirm your interest in the role. Keep it to 3-4 sentences.",
        ],
    ),
    (
        ['mock interview', 'practice interview'],
        [
            "Mock interviews work best when you say your answers out loud, ideally to another person or recorded on your phone — thinking an answer in your head feels very different from actually saying it under a bit of pressure.",
        ],
    ),
    (
        ['ghosted', 'no response after interview', 'havent heard back'],
        [
            "If it's been over a week past when they said you'd hear back, send one polite follow-up email asking for a status update — after that, it's reasonable to treat it as a no and keep applying elsewhere. Don't let one company stall your whole search.",
        ],
    ),
    (
        ['interview'],
        [
            "For interviews: research the company's recent news and products, prepare 2-3 STAR-format stories (Situation, Task, Action, Result) you can adapt to different questions, and always have 2-3 questions ready to ask them. Practice saying your answers out loud, not just in your head.",
            "A great way to prep is the STAR method — Situation, Task, Action, Result — for behavioral questions like 'tell me about a time you...'. Want me to walk through an example?",
        ],
    ),
    (
        ['salary', 'negotiat', 'pay', 'compensation', 'ctc'],
        [
            "When negotiating salary: let them name a number first if you can, research the market range beforehand (Glassdoor, Levels.fyi, LinkedIn), and negotiate the total package — base, bonus, equity, PTO — not just base salary. It's normal to ask for 24-48 hours to consider an offer.",
        ],
    ),
    (
        ['job offer', 'multiple offers', 'accept offer', 'decline offer'],
        [
            "Get every offer in writing before you decide, compare total compensation (not just base pay) plus growth and team fit, and if you're comparing multiple offers it's fine to tell each company honestly that you're weighing options — most will give you a bit more time.",
        ],
    ),
    (
        ['linkedin'],
        [
            "For LinkedIn: use a clear headshot, write a headline that says what you do (not just your job title), and turn your 'About' section into a short story of your career, not a list. Posting or commenting occasionally keeps you visible to recruiters searching your field.",
        ],
    ),
    (
        ['network', 'networking', 'referral', 'cold email', 'cold message'],
        [
            "A short, specific outreach message beats a generic one every time: mention something real about their work, ask one focused question or for 15 minutes of their time, and don't ask for a job directly in the first message. Referrals get noticed far more than cold applications.",
        ],
    ),
    (
        ['recruiter', 'headhunter'],
        [
            "Recruiters move faster when you make it easy: a clean, up-to-date resume, a clear one-line summary of what you're looking for, and a quick reply when they reach out. Building a relationship with a few good recruiters in your field pays off over your whole career, not just one job.",
        ],
    ),
    (
        ['remote job', 'remote work', 'work from home'],
        [
            "For remote roles, emphasize self-management on your resume — projects you drove independently, async communication, and tools you've used (Slack, Notion, Zoom, Git). In interviews, be ready to talk through how you structure your day without someone checking in on you.",
        ],
    ),
    (
        ['internship', 'intern'],
        [
            "For internship applications, coursework and class projects absolutely count as experience — describe them with the same action-verb, result-focused style as a real job. Apply early; many internship cycles open 6+ months before the actual start date.",
        ],
    ),
    (
        ['freelance', 'freelancing', 'gig work'],
        [
            "List freelance work on your resume just like a job — client/project name, what you delivered, and the measurable outcome. A simple one-page portfolio site with 2-3 case studies makes freelance experience far more credible to a hiring manager.",
        ],
    ),
    (
        ['career change', 'switch careers', 'change field'],
        [
            "For a career change, lead with transferable skills (problem-solving, leadership, communication) and reframe past experience in the new field's language, then fill any real gaps with a short course or personal project you can point to. Your cover letter should directly address the 'why' of the switch.",
        ],
    ),
    (
        ['layoff', 'laid off', 'fired', 'let go'],
        [
            "A layoff is common and rarely held against you — you can state it plainly ('the team was restructured') without over-explaining. Focus your energy forward: update your resume with your latest achievements and get back into applying within a few days if you can, momentum matters.",
        ],
    ),
    (
        ['job search', 'find a job', 'looking for a job', 'job hunt', 'apply for job', 'job hunting'],
        [
            "Job searching works best with a mix: apply to roles online, but also reach out directly to people at companies you like — a short, specific message asking for 15 minutes of their time beats a cold application most of the time. Track every application in a spreadsheet so you can follow up on time.",
        ],
    ),
    (
        ['job description', 'job posting'],
        [
            "Read the job description line by line and mirror its exact keywords in your resume's skills and bullet points — that's what both ATS software and a skimming recruiter are scanning for first. Our Resume Optimizer does this comparison automatically.",
        ],
    ),
    (
        ['fresher', 'no experience', 'entry level', 'first job'],
        [
            "With no formal experience yet, lean on projects, coursework, internships, and volunteer work — treat them like real jobs on your resume with the same action-verb, result-focused bullet style. Employers hiring entry-level care more about problem-solving ability than years on paper.",
        ],
    ),
    (
        ['nervous', 'anxious', 'anxiety', 'stress', 'scared', 'overwhelmed'],
        [
            "It's completely normal to feel nervous before interviews or big applications. Preparing a few solid stories in advance and doing a couple of mock run-throughs (even just talking to a mirror) usually brings the nerves down a lot by the time it's real.",
        ],
    ),
    (
        ['study', 'studying', 'revise', 'revision'],
        [
            "For studying: spaced repetition beats cramming — review material a day, then a week, then a month later instead of all at once. Active recall (quizzing yourself, explaining concepts out loud) sticks far better than just re-reading notes.",
            "Try the Pomodoro technique — 25 minutes focused study, 5 minute break — and switch topics rather than grinding one subject for hours. It keeps your brain from tuning out.",
        ],
    ),
    (
        ['exam', 'test prep', 'memoriz'],
        [
            "Before an exam, do at least one full practice test under timed conditions — it exposes gaps real reading never does. Sleep matters more than one extra late-night hour; a rested brain recalls information far better than an exhausted one.",
        ],
    ),
    (
        ['procrastinat'],
        [
            "The fastest fix for procrastination is shrinking the first step — 'write the essay' feels huge, but 'open the doc and write one sentence' doesn't. Momentum from that tiny start is usually enough to keep going.",
        ],
    ),
    (
        ['time management', 'schedule', 'productivity'],
        [
            "Time-block your calendar the night before instead of relying on a mental to-do list, and tackle your hardest or most important task first thing — willpower is highest early in the day and drains as it goes on.",
        ],
    ),
    (
        ['focus', 'concentration', 'distract'],
        [
            "Put your phone in another room, not just face-down — proximity alone measurably hurts focus. Work in short, timed blocks (like Pomodoro) rather than open-ended 'study for a while' sessions, which tend to dissolve into distraction.",
        ],
    ),
    (
        ['note taking', 'notes', 'note-taking'],
        [
            "Write notes in your own words rather than copying slides verbatim — the act of rephrasing is what actually builds memory. Reviewing and condensing your notes within 24 hours of taking them locks them in far better than reading them once before an exam.",
        ],
    ),
    (
        ['motivation', 'burnout', 'lazy', 'unmotivated'],
        [
            "Low motivation is often a sign you need rest or a smaller next step, not more willpower — break the task down until the next action feels almost too easy to skip, and build in real breaks so you're not running on empty.",
        ],
    ),
    (
        ['public speaking', 'presentation skills', 'presenting'],
        [
            "For presentations, practice out loud at least 3 times (not just in your head), open with why your audience should care before diving into detail, and it's fine to have small note cards — nobody expects you to have it all memorized.",
        ],
    ),
    (
        ['gpa', 'grades', 'semester', 'college', 'university'],
        [
            "A strong GPA helps but isn't everything — most employers care more about projects, internships, and what you can actually do. If your GPA isn't your strongest point, let your resume's project and experience sections do the talking instead.",
        ],
    ),
    (
        ['skill', 'learn', 'upskill', 'course', 'certification'],
        [
            "Pick skills based on what actually shows up in job postings you want, not just what's trendy — search a few listings and note the recurring requirements. Free resources like freeCodeCamp, Coursera audits, or official docs are usually enough to build a real project you can put on your resume.",
        ],
    ),
    (
        ['what can you do', 'help me with', 'what do you do', 'who are you', 'what is this'],
        [
            "I can help with resume writing, ATS optimization, job search strategy, interview prep, and general study tips. Ask me something like 'how do I make my resume ATS-friendly' or 'tips for a behavioral interview'.",
        ],
    ),
]

_FALLBACK_REPLIES = [
    "I'm mainly tuned for resumes, job search, studying, and interview prep — could you rephrase your question around one of those?",
    "I don't have a great answer for that one yet. Try asking about resume tips, ATS, interview prep, or study habits.",
    "Not sure I follow — I'm best at resume, job hunting, study, and interview questions. Could you ask it a different way?",
]


def _tokenize(text):
    """Lowercase, punctuation-free word list used for fuzzy matching."""
    return re.findall(r"[a-z']+", text.lower())


def _edit_distance(a, b, max_dist):
    """
    Damerau-Levenshtein distance (insert/delete/substitute/transpose)
    between a and b, capped early past max_dist. Transposition support
    matters because typos like 'jbo' for 'job' are extremely common.
    """
    if abs(len(a) - len(b)) > max_dist:
        return max_dist + 1
    la, lb = len(a), len(b)
    prev2 = None
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            val = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                val = min(val, prev2[j - 2] + 1)
            curr[j] = val
        prev2, prev = prev, curr
    return prev[lb]


def _max_allowed_distance(word_len):
    """How many typo'd characters we'll tolerate, scaled to word length."""
    if word_len <= 2:
        return 0   # too short to fuzzy-match safely (e.g. 'cv')
    if word_len <= 5:
        return 1
    if word_len <= 8:
        return 2
    return 3


def _word_fuzzy_match(token, keyword_word):
    """True if `token` is an exact or typo-close match to `keyword_word`."""
    if token == keyword_word:
        return True
    max_dist = _max_allowed_distance(len(keyword_word))
    if max_dist == 0:
        return False
    return _edit_distance(token, keyword_word, max_dist) <= max_dist


def _keyword_matches(tokens, lowered_text, keyword):
    """
    True if `keyword` (one or more words) is present in the message —
    either as an exact substring, or, word-for-word, as a typo-tolerant
    fuzzy match against the message's tokens (order-independent).
    """
    if keyword in lowered_text:
        return True
    keyword_words = keyword.split()
    return all(
        any(_word_fuzzy_match(token, kw_word) for token in tokens)
        for kw_word in keyword_words
    )


def get_chatbot_reply(message):
    """Return a canned reply matched (typo-tolerant) against `message`."""
    if not message:
        return "Ask me anything about resumes, job hunting, studying, or interviews!"

    lowered = message.lower()
    tokens = _tokenize(lowered)

    for keywords, replies in _CHATBOT_RULES:
        if any(_keyword_matches(tokens, lowered, kw) for kw in keywords):
            return random.choice(replies)

    return random.choice(_FALLBACK_REPLIES)
