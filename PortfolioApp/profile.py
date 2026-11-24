from sqlalchemy.dialects.sqlite import insert

from . import db
from .models import SiteProfile


WORK = (
    {
        "slug": "business-intelligence",
        "company": "Ghassan Aboud Group",
        "role": "Manager, Business Intelligence & Analytics",
        "location": "Dubai, UAE",
        "period": "Joined in 2021",
        "title": "One view across eight businesses",
        "intro": "I helped build a shared BI function so finance and operating teams could work from the same figures.",
        "story": "The group’s businesses relied on seven different source systems. I led work on the shared data infrastructure and helped standardize the models behind reports, so teams could compare results across businesses.",
        "outcome": "The group automated financial reporting across all eight affiliate businesses.",
        "art": "teal",
        "figure": "8",
        "figure_label": "affiliate businesses",
    },
    {
        "slug": "cargo-visibility",
        "company": "DP World",
        "role": "Data Scientist",
        "location": "Dubai / Hyderabad",
        "period": "2020–2021",
        "title": "Filling gaps in cargo journeys",
        "intro": "Containers change hands during a journey, and some movements never get a recorded timestamp.",
        "story": "I developed and deployed a statistical model to estimate when missing events occurred as containers moved between modes of transport.",
        "outcome": "I integrated the estimates into an in-house customer-facing product through a serverless API.",
        "art": "logistics",
        "figure": "Cargo",
        "figure_label": "event timelines",
    },
    {
        "slug": "decision-science",
        "company": "Mu Sigma",
        "role": "Decision Scientist",
        "location": "Bengaluru, India",
        "period": "Joined in 2016",
        "title": "Finding evidence in healthcare data",
        "intro": "I helped life sciences teams study what happens to people in everyday care using claims and electronic health records.",
        "story": "I designed and delivered real-world evidence studies across three therapeutic areas. In one project, I developed a way to study caregiver burden using unstructured text.",
        "outcome": "Findings were presented at conferences and published in journals.",
        "art": "sand",
        "figure": "12+",
        "figure_label": "research studies",
    },
)


DEFAULT_PROFILE = {
    "tagline": "Data & Decision Sciences",
    "headline": "Data with",
    "headline_accent": "direction.",
    "intro": "I help teams make sense of data they use every day, from finance reports to container movements and health records.",
    "location": "Dubai, UAE",
    "about_lead": "I build data systems and use them to help people make decisions.",
    "about_text": (
        "My first years in analytics were in Bengaluru, where I worked with healthcare claims and electronic health records"
        " to answer research questions. At DP World, I worked on a different puzzle: how to piece together a container’s"
        " journey when some of the timestamps are missing.\n\n"
        "In Dubai, I helped build a business intelligence function for a group with eight affiliate businesses. That work"
        " meant bringing data from different systems together and agreeing on what a number should mean before putting it"
        " on a dashboard.\n\n"
        "One question runs through all of it: what will someone do differently once they have this information?"
    ),
    "resume_headline": "Business Intelligence & Analytics · Dubai, UAE",
    "work": [{**entry, "featured": "yes"} for entry in WORK],
    "education": [
        {"institution": "SP Jain School of Global Management", "period": "2023", "title": "MBA, Finance"},
        {"institution": "M. S. Ramaiah Institute of Technology", "period": "2017",
         "title": "Bachelor of Engineering, Industrial Engineering & Management"},
    ],
    "skills": [
        {"title": "Data platforms and BI", "description": "SQL, Snowflake, BigQuery, Matillion, Power BI, and Tableau."},
        {"title": "Analysis and modeling", "description": "Python, R, and SAS for statistical modeling, text analysis, and research."},
    ],
    "publications": [
        {"title": "Demographic characteristics, healthcare costs, and treatment patterns in major depressive disorder",
         "url": "https://s3.amazonaws.com/HMP/hmp_ln/imported/2019-12/320-Demographic-Characteristics-Healthcare-Cost-an.pdf"},
        {"title": "Costs of inflammatory bowel disease–related hospitalizations",
         "url": "https://journals.lww.com/ajg/Fulltext/2020/10001/S0871_Costs_of_Inflammatory_Bowel_Disease_Related.872.aspx"},
    ],
}


def read_profile():
    record = db.session.get(SiteProfile, 1)
    return (record.content, record.revision) if record else (DEFAULT_PROFILE, 0)


def save_profile(content, revision):
    if revision:
        result = db.session.execute(
            db.update(SiteProfile).where(SiteProfile.id == 1, SiteProfile.revision == revision)
            .values(content=content, revision=revision + 1)
        )
    else:
        result = db.session.execute(
            insert(SiteProfile).values(id=1, revision=1, content=content).on_conflict_do_nothing()
        )
    db.session.commit()
    return result.rowcount == 1
