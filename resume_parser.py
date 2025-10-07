import os
import re
from datetime import datetime
import fitz  # PyMuPDF

# --- Configuration: Job Role Definitions ---
# This dictionary now has more nuanced keywords to better match related roles.
JOB_ROLES = {
    "Data Analyst": {
        "experience_range": (1, 5),
        "mandatory_keywords": ["sql", "excel", "tableau", "power bi"],
        "positive_keywords": ["analyst", "analytics", "dashboard", "reporting", "python", "r", "statistics", "visualization", "data engineer", "etl"]
    },
    "Junior Developer": {
        "experience_range": (0, 3),
        "mandatory_keywords": ["python", "git", "sql"],
        "positive_keywords": ["developer", "software", "engineer", "code", "programming", "flask", "django", "api"]
    },
    "DevOps Engineer": {
        "experience_range": (2, 7),
        "mandatory_keywords": ["aws", "docker", "kubernetes", "ci/cd", "terraform"],
        "positive_keywords": ["devops", "infrastructure", "automation", "cloud", "sysadmin", "jenkins", "ansible"]
    },
    "Machine Learning Engineer": {
        "experience_range": (2, 8),
        "mandatory_keywords": ["python", "tensorflow", "pytorch", "scikit-learn", "sql"],
        "positive_keywords": ["machine learning", "ml", "ai", "artificial intelligence", "deep learning", "nlp", "computer vision"]
    },
    "Frontend Developer": {
        "experience_range": (1, 6),
        "mandatory_keywords": ["html", "css", "javascript", "react", "git"],
        "positive_keywords": ["frontend", "ui", "ux", "web developer", "angular", "vue", "typescript"]
    }
}

# --- Configuration: Master Skill Database ---
# Expanded with the skills from the Data Engineer resume.
SKILLS_DB = [
    'python', 'java', 'c++', 'sql', 'javascript', 'html', 'css', 'git', 'docker', 'kubernetes',
    'aws', 'azure', 'gcp', 'react', 'angular', 'vue', 'django', 'flask', 'fastapi',
    'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy', 'matplotlib', 'seaborn',
    'tableau', 'power bi', 'excel', 'r', 'ci/cd', 'jenkins', 'ansible', 'terraform', 'nlp',
    'computer vision', 'apache spark', 'hadoop', 'airflow', 'aws redshift', 'etl'
]

# --- Core Parsing Functions ---

def _extract_text_from_pdf(filepath: str) -> str:
    """Extracts all text from a PDF file."""
    try:
        with fitz.open(filepath) as doc:
            text = "".join(page.get_text() for page in doc)
        return text.lower()  # Convert to lowercase for case-insensitive matching
    except Exception as e:
        print(f"Error reading PDF {filepath}: {e}")
        return ""

def _get_experience_years(text: str) -> int:
    """
    UPGRADED: Extracts years of experience by finding date ranges using regular expressions.
    This is much more accurate than the previous implementation.
    """
    # Regex to find patterns like (2019-2024), 2019 - 2024, 2019 to Present, etc.
    year_ranges = re.findall(r'(\b(20\d{2})\b)\s*[-–—to]\s*(\b(20\d{2}|present|current)\b)', text, re.IGNORECASE)
    
    if not year_ranges:
        # If no ranges found, look for standalone years as a fallback.
        years = re.findall(r'\b20\d{2}\b', text)
        if not years:
            return 0
        # Estimate experience based on the span of mentioned years
        unique_years = sorted([int(y) for y in set(years)])
        return (unique_years[-1] - unique_years[0]) if len(unique_years) > 1 else 1

    max_duration = 0
    current_year = datetime.now().year

    for start_year_str, _, end_year_str, _ in year_ranges:
        start_year = int(start_year_str)
        if end_year_str.lower() in ['present', 'current']:
            end_year = current_year
        else:
            end_year = int(end_year_str)
        
        duration = end_year - start_year
        if duration > max_duration:
            max_duration = duration
            
    return max_duration if max_duration > 0 else 1 # Return at least 1 year if a range is found

def _find_skills(text: str) -> list:
    """Finds skills from the SKILLS_DB in the resume text."""
    found_skills = []
    for skill in SKILLS_DB:
        # Use regex for whole-word matching to avoid partial matches (e.g., 'r' in 'reporting')
        if re.search(r'\b' + re.escape(skill) + r'\b', text):
            found_skills.append(skill)
    return sorted(list(set(found_skills)))

def parse_and_score_resume(filepath: str, role_name: str) -> dict:
    """
    Main function to parse a resume, score it against a role, and return the analysis.
    """
    if role_name not in JOB_ROLES:
        raise ValueError(f"Invalid role '{role_name}'.")

    role_reqs = JOB_ROLES[role_name]
    text = _extract_text_from_pdf(filepath)

    if not text:
        return {"error": "Could not read text from the resume file."}

    # --- Data Extraction ---
    extracted_experience = _get_experience_years(text)
    extracted_skills = _find_skills(text)

    # --- Scoring Logic ---
    # 1. Semantic Fit Score (based on positive keywords)
    semantic_score = 0
    for keyword in role_reqs["positive_keywords"]:
        if keyword in text:
            semantic_score += 1
    # Scale score to be out of 100
    semantic_score_scaled = min((semantic_score / 5) * 100, 100) # Capped at 5 keywords

    # 2. Mandatory Keyword Score
    skill_gaps = []
    keywords_found = 0
    for req_skill in role_reqs["mandatory_keywords"]:
        if req_skill in extracted_skills:
            keywords_found += 1
        else:
            skill_gaps.append(req_skill)
    keyword_score_scaled = (keywords_found / len(role_reqs["mandatory_keywords"])) * 100

    # --- Final Bias-Free Score (Weighted Average) ---
    total_score = (semantic_score_scaled * 0.5) + (keyword_score_scaled * 0.5)

    # --- Recommendation Logic ---
    exp_min, exp_max = role_reqs["experience_range"]
    recommendation = ""
    explanation = ""

    if extracted_experience > exp_max:
        recommendation = "Potential Fit (Overqualified)"
        explanation = f"Candidate has ~{extracted_experience} years of experience, exceeding the role's maximum of {exp_max} years."
    elif extracted_experience < exp_min:
        recommendation = "Not a Fit (Underqualified)"
        explanation = f"Candidate has only ~{extracted_experience} years of experience, below the minimum {exp_min} years required."
    elif total_score >= 80:
        recommendation = "Strong Fit"
        explanation = f"Candidate's ~{extracted_experience} years of experience is a perfect match for this role, with strong keyword alignment."
    elif total_score >= 60:
        recommendation = "Good Fit"
        explanation = f"Candidate meets the experience criteria and has a good set of matching skills."
    else:
        recommendation = "Near-Fit Candidate (Offer Learning Path)"
        explanation = "Candidate meets the experience criteria but has some skill gaps that could be addressed with training."


    # --- Format the final result for the frontend ---
    return {
        "Total_Score_Bias_Free": total_score,
        "F_semantic_scaled": semantic_score_scaled,
        "F_keyword_scaled": keyword_score_scaled,
        "Recommendation": recommendation,
        "Explanation": explanation,
        "Skill_Gaps": skill_gaps,
        "Top_Skills": extracted_skills,
    }

