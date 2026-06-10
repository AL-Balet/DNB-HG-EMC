import html
import json
import re
import os
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://eduscol.education.gouv.fr/5202/preparer-le-diplome-national-du-brevet-dnb-avec-les-sujets-des-annales?page=%2C11"
HTML_PATH = ROOT / ".cache" / "eduscol" / "page.html"
DATA_PATH = ROOT / "data.js"
DATA_JSON_PATH = ROOT / "data.json"
PDF_CACHE = ROOT / ".cache" / "eduscol" / "pdfs"
ANNEX_DIR = ROOT / "assets" / "annexes"
DOCUMENT_DIR = ROOT / "assets" / "documents"
POPPLER_PATH = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "native" / "poppler" / "bin"
POPPLER_FULL_PATH = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "native" / "poppler" / "poppler" / "bin"

CHAPTER_RULES = [
    {
        "subject": "Histoire",
        "chapter": "H-01 : Première Guerre mondiale",
        "keywords": ["première guerre mondiale", "grande guerre", "1914", "1918", "tranchée", "tranchées", "poilus", "armistice", "génocide des arméniens", "civils et militaires"],
    },
    {
        "subject": "Histoire",
        "chapter": "H-02 : Régimes totalitaires et démocraties fragilisées",
        "keywords": ["régimes totalitaires", "démocraties fragilisées", "entre-deux-guerres", "stalin", "urss", "hitler", "nazi", "nazisme", "front populaire", "totalitaire", "totalitarisme"],
    },
    {
        "subject": "Histoire",
        "chapter": "H-03 : Seconde Guerre mondiale",
        "keywords": ["seconde guerre mondiale", "deuxième guerre mondiale", "guerre d'anéantissement", "1939", "1945", "shoah", "auschwitz", "juifs", "tziganes", "génocide"],
    },
    {
        "subject": "Histoire",
        "chapter": "H-04 : France occupée, régime de Vichy et Résistance",
        "keywords": ["france occupée", "vichy", "pétain", "collaboration", "résistance", "appel du 18 juin", "de gaulle", "occupation", "libération"],
    },
    {
        "subject": "Histoire",
        "chapter": "H-05 : Décolonisation et indépendances",
        "keywords": ["décolonisation", "indépendance", "indépendances", "algérie", "inde", "nouveaux états", "empire colonial", "colonies"],
    },
    {
        "subject": "Histoire",
        "chapter": "H-06 : Guerre froide",
        "keywords": ["guerre froide", "monde bipolaire", "états-unis", "urss", "berlin", "cuba", "rideau de fer", "bloc de l'est", "bloc de l'ouest"],
    },
    {
        "subject": "Histoire",
        "chapter": "H-07 : Construction européenne",
        "keywords": ["construction européenne", "projet européen", "traité de rome", "cee", "maastricht", "affirmation et mise en œuvre du projet européen"],
    },
    {
        "subject": "Histoire",
        "chapter": "H-08 : Le monde depuis 1989",
        "keywords": ["depuis 1989", "après 1989", "monde depuis 1989", "conflits", "terrorisme", "onu", "nouvel ordre mondial"],
    },
    {
        "subject": "Histoire",
        "chapter": "H-09 : Refonder la République (1944-1947)",
        "keywords": ["refonder la république", "1944", "1947", "conseil national de la résistance", "cnr", "droit de vote des femmes", "sécurité sociale"],
    },
    {
        "subject": "Histoire",
        "chapter": "H-10 : La Ve République",
        "keywords": ["ve république", "cinquième république", "de gaulle", "1958", "cohabitation", "alternance", "institutions"],
    },
    {
        "subject": "Histoire",
        "chapter": "H-11 : Évolutions de la société française depuis les années 1950",
        "keywords": ["évolutions de la société française", "années 1950", "années 1980", "société française", "immigration", "jeunesse", "droits des femmes", "ivg", "chômage"],
    },
    {
        "subject": "Geographie",
        "chapter": "G-01 : Les aires urbaines françaises",
        "keywords": ["aires urbaines", "aire urbaine", "urbanisation", "périurbain", "périurbanisation", "mobilités quotidiennes", "métropole"],
    },
    {
        "subject": "Geographie",
        "chapter": "G-02 : Les espaces productifs",
        "keywords": ["espaces productifs", "espace productif", "industrie", "industriel", "agricole", "touristique", "mondialisation"],
    },
    {
        "subject": "Geographie",
        "chapter": "G-03 : Les espaces de faible densité",
        "keywords": ["faible densité", "espaces ruraux", "montagnes", "parc naturel", "tourisme vert", "néoruraux", "atouts"],
    },
    {
        "subject": "Geographie",
        "chapter": "G-04 : Aménager le territoire français",
        "keywords": ["aménager", "aménagement", "inégalités", "territoire français", "territoires français", "acteurs", "collectivités", "équipements publics"],
    },
    {
        "subject": "Geographie",
        "chapter": "G-05 : Les territoires ultramarins",
        "keywords": ["ultramarins", "ultra-marins", "ultra-marin", "outre-mer", "drom", "guadeloupe", "martinique", "réunion", "mayotte", "guyane"],
    },
    {
        "subject": "Geographie",
        "chapter": "G-06 : L'Union européenne",
        "keywords": ["union européenne", "ue", "territoire de référence", "appartenance", "région transfrontalière", "euro"],
    },
    {
        "subject": "Geographie",
        "chapter": "G-07 : La France et l'Europe dans le monde",
        "keywords": ["france et l'europe dans le monde", "puissance", "influence", "francophonie", "diplomatie", "rayonnement mondial"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-01 : Respect de soi et des autres",
        "keywords": ["respect de soi", "respect des autres", "respect d'autrui", "harcèlement", "vie privée", "dignité"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-02 : Discriminations et égalité",
        "keywords": ["discrimination", "discriminations", "égalité", "égalités", "égalité hommes-femmes", "égalité femmes-hommes", "racisme", "sexisme"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-03 : Laïcité",
        "keywords": ["laïcité", "charte de la laïcité", "liberté de conscience", "religion"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-04 : Libertés, droits et devoirs",
        "keywords": ["libertés", "droits et devoirs", "droits fondamentaux", "liberté d'expression", "liberté de la presse", "droits de l'homme", "droit au logement", "mal-logement", "précarité"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-05 : Justice et État de droit",
        "keywords": ["justice", "état de droit", "loi dans une démocratie", "à quoi sert la loi", "loi elan", "marchands de sommeil", "tribunal", "loi", "sanction", "défenseur des droits"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-06 : Valeurs et symboles de la République",
        "keywords": ["valeurs de la république", "valeurs républicaines", "principes de la république", "symboles de la république", "sécurité sociale", "solidarité", "fraternité", "liberté égalité fraternité", "république indivisible laïque démocratique et sociale", "commune", "drapeau", "marseillaise", "devise", "république française"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-07 : Citoyenneté française et européenne",
        "keywords": ["citoyenneté française", "citoyenneté européenne", "citoyen européen", "union européenne", "erasmus", "nationalité"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-08 : Démocratie et participation citoyenne",
        "keywords": ["démocratie", "participation citoyenne", "démocratie participative", "comités consultatifs", "conseil municipal", "conseil de la vie collégienne", "cvc", "débat", "représentation démocratique"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-09 : Le vote et les élections",
        "keywords": ["vote", "élection", "élections", "scrutin", "abstention", "suffrage universel", "électeur"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-10 : Médias, information et esprit critique",
        "keywords": ["médias", "information", "esprit critique", "réseaux sociaux", "fake news", "rumeur", "désinformation"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-11 : Défense et sécurité",
        "keywords": ["défense nationale", "sécurité nationale", "sécurité civile", "cadets de la sécurité", "sapeurs-pompiers", "sapeurs pompiers", "incendie", "armée jeunesse", "sma", "service militaire adapté", "journée défense", "jdc", "armée", "risques majeurs"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-12 : Engagement citoyen",
        "keywords": ["engagement", "engagement citoyen", "jeune sapeur-pompier", "jeunes sapeurs-pompiers", "association", "bénévolat", "service civique", "responsabilité", "lanceur d'alerte"],
    },
    {
        "subject": "EMC",
        "chapter": "EMC-13 : Développement durable et responsabilité citoyenne",
        "keywords": ["développement durable", "responsabilité citoyenne", "mesures barrières", "covid", "propagation", "santé publique", "pandémie", "environnement", "écologie", "climat", "risque", "tsunami"],
    },
]


def strip_html(value):
    text = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(html.unescape(text).split())


def extract_database(raw_html):
    start = raw_html.find('[{"session"')
    if start == -1:
        raise RuntimeError("Base Eduscol introuvable dans la page.")

    decoder = json.JSONDecoder()
    data, _ = decoder.raw_decode(raw_html[start:])
    return data


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def pick_primary_link(links):
    pdf_links = [link for link in links if link["url"].lower().endswith(".pdf")]
    for link in pdf_links:
        if link["label"].strip().lower() == "sujet":
            return link
    return pdf_links[0] if pdf_links else None


def pdf_cache_path(url, cache_dir):
    filename = cache_dir / Path(url.split("?")[0]).name
    return filename


def ensure_pdf_cached(url, cache_dir):
    filename = pdf_cache_path(url, cache_dir)
    if not filename.exists():
        with urllib.request.urlopen(url, timeout=25) as response:
            filename.write_bytes(response.read())
    return filename


def read_pdf_pages(filename):
    reader = PdfReader(str(filename))
    return [(page.extract_text() or "") for page in reader.pages]


def extract_pdf_text(url, cache_dir):
    if os.environ.get("SKIP_PDF_TEXT") == "1":
        return ""

    filename = ensure_pdf_cached(url, cache_dir)

    try:
        pages = read_pdf_pages(filename)
    except Exception as exc:
        return f"Texte non extrait automatiquement ({exc})."

    text = "\n".join(pages)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_for_match(value):
    accents = str.maketrans("àâäéèêëîïôöùûüçœ’`", "aaaeeeeiioouuucœ''")
    return value.lower().translate(accents)


def extract_exam_code(text):
    match = re.search(r"\b\d{2}[-_\s]*GEN[-_\s]*HGEMC[-_\s]*[A-Z0-9]{2,}\b", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"\b\d{2}GENHGEMC[_A-Z0-9]{2,}\b", text, flags=re.IGNORECASE)
    if not match:
        return ""

    code = re.sub(r"[-_\s]+", "", match.group(0)).upper()
    return re.sub(r"PDF$", "", code)


def classify_chapters(text):
    normalized = normalize_for_match(text)
    matches = []

    for rule in CHAPTER_RULES:
        score = 0
        for keyword in rule["keywords"]:
            key = normalize_for_match(keyword)
            if key in normalized:
                score += 3 if " " in key else 1
        if score >= 3:
            matches.append({**rule, "score": score})

    matches.sort(key=lambda item: (-item["score"], item["chapter"]))
    selected = []
    seen_subjects = set()
    for item in matches:
        if item["subject"] not in seen_subjects:
            selected.append(item)
            seen_subjects.add(item["subject"])

    if not selected:
        return [{"subject": "À vérifier", "chapter": "À vérifier"}]

    return selected[:3]


def official_chapter_from_title(title, subject):
    title_norm = normalize_for_match(title)
    candidates = [rule for rule in CHAPTER_RULES if rule["subject"] == subject]

    for rule in candidates:
        chapter_norm = normalize_for_match(rule["chapter"])
        if chapter_norm in title_norm or title_norm in chapter_norm:
            return {"subject": subject, "chapter": rule["chapter"], "score": 50}

    scored = []
    for rule in candidates:
        score = 0
        for keyword in rule["keywords"]:
            key = normalize_for_match(keyword)
            if key in title_norm:
                score += 3 if " " in key else 1
        if score:
            scored.append({**rule, "score": score})

    if scored:
        scored.sort(key=lambda item: (-item["score"], item["chapter"]))
        return scored[0]

    return None


def read_title_after_label(lines, index, label):
    line = lines[index]
    match = re.match(r"^[A-Za-zÉÈÊËÀÂÎÏÔÙÛÇéèêëàâîïôùûç ]+\s*[:\-–.]\s*(.*)$", line)
    rest = match.group(1) if match else ""
    parts = [rest.strip()]
    stop_prefixes = (
        "document",
        "questions",
        "question",
        "source",
        "exercice",
        "1.",
        "2.",
        "3.",
        "4.",
        "5.",
    )

    for next_line in lines[index + 1 : index + 6]:
        clean = next_line.strip()
        if not clean:
            if parts and any(parts):
                break
            continue
        lowered = normalize_for_match(clean)
        if lowered.startswith(stop_prefixes):
            break
        if label == "EMC" and (lowered.startswith("depuis ") or lowered.startswith("dans ")):
            break
        parts.append(clean)
        if clean.endswith(".") or clean.endswith("?"):
            break

    return " ".join(part for part in parts if part).strip()


def extract_declared_classifications(text):
    lines = [line.strip() for line in text.splitlines()]
    found = []

    for index, line in enumerate(lines):
        normalized = normalize_for_match(line)

        if (re.match(r"^histoire\s*[:\-–.]", normalized) or normalized == "histoire") and "histoire-geographie" not in normalized:
            title = read_title_after_label(lines, index, "Histoire")
            chapter = official_chapter_from_title(title, "Histoire")
            if chapter:
                found.append(chapter)

        if (re.match(r"^geographie\s*[:\-–.]", normalized) or normalized == "geographie") and "histoire-geographie" not in normalized:
            title = read_title_after_label(lines, index, "Geographie")
            chapter = official_chapter_from_title(title, "Geographie")
            if chapter:
                found.append(chapter)

        if re.match(r"^situation pratique\s*[:\-–.]", normalized):
            title = read_title_after_label(lines, index, "EMC")
            chapter = official_chapter_from_title(title, "EMC")
            if chapter:
                found.append(chapter)

    deduped = []
    seen_subjects = set()
    for item in found:
        if item["subject"] not in seen_subjects:
            deduped.append(item)
            seen_subjects.add(item["subject"])

    return deduped


def complete_classifications(text, declared):
    by_subject = {item["subject"]: item for item in declared}

    if len(by_subject) == 3:
        return [by_subject[subject] for subject in ["Histoire", "Geographie", "EMC"]]

    for item in classify_chapters(text):
        by_subject.setdefault(item["subject"], item)

    defaults = {
        "Histoire": "Histoire",
        "Geographie": "Géographie",
        "EMC": "Enseignement moral et civique",
    }
    for subject, chapter in defaults.items():
        by_subject.setdefault(subject, {"subject": subject, "chapter": chapter, "score": 0})

    return [by_subject[subject] for subject in ["Histoire", "Geographie", "EMC"] if subject in by_subject]


def infer_subjects(text):
    normalized = text.lower()
    subjects = []
    if "histoire" in normalized:
        subjects.append("Histoire")
    if "géographie" in normalized or "geographie" in normalized:
        subjects.append("Geographie")
    if "enseignement moral et civique" in normalized or "emc" in normalized:
        subjects.append("EMC")
    return subjects or ["Histoire", "Geographie", "EMC"]


def infer_types(text):
    normalized = text.lower()
    normalized_for_match = normalize_for_match(text)
    exercise_2_blocks = re.findall(r"exercice\s*2(.+?)(?=exercice\s*3|$)", normalized_for_match, flags=re.DOTALL)
    exercise_2 = "\n".join(exercise_2_blocks) if exercise_2_blocks else normalized_for_match
    types = []
    if "analyse" in normalized or "document" in normalized:
        types.append("Analyse de document")
    if "développement construit" in normalized or "developpement construit" in normalized:
        types.append("Developpement construit")
    if "histoire" in exercise_2 or any(term in exercise_2 for term in ["reperes historiques", "frise", "chronologique", "datez", "dates reperes"]):
        types.append("Reperes historiques")
    if "geographie" in exercise_2 or any(term in exercise_2 for term in ["reperes geographiques", "reperes cartographiques", "carte", "croquis", "schema", "planisphere", "localisez", "localiser", "nommez", "nommer"]):
        types.append("Reperes geographiques")
    if "enseignement moral et civique" in normalized or "emc" in normalized:
        types.append("EMC")
    return types or ["Sujet complet"]


def is_boilerplate_line(line):
    normalized = normalize_for_match(line)
    normalized = re.sub(r"[\u00a0\u202f]", " ", normalized)
    compact = re.sub(r"\s+", " ", normalized).strip()

    if not compact:
        return False

    patterns = [
        r"^\d{2}genhgemc.*page \d+/\d+",
        r"^\d{2}genhgemc[_a-z0-9]*\s*page \d+\s*/\s*\d+",
        r"^\d{2}genhgemc.*page \d+ sur \d+",
        r"^\d{2}genhgemc[_a-z0-9]*\s*\d+\s*/\s*\d+",
        r"^\d{2}genhgemc[_a-z0-9]*\s*page agrandie",
        r"^\d{2}genhgemc.*diplome national du brevet.*page \d+/\d+",
        r"^\d{2}genhgemc.*dnb serie generale.*page \d+ sur \d+",
        r"^\d{2}genhgemc[_a-z0-9]*\s*dnb serie generale$",
        r"^\d{2}genhgemc[a-z0-9]*$",
        r"^\d{2}genhgemc_[a-z0-9]*$",
        r"^diplome national du brevet$",
        r"^diplome national du brevet.*$",
        r"^diplome national du brevet page \d+/\d+.*$",
        r"^examen ou concours",
        r"^session :",
        r"^repere de l'epreuve",
        r"^intitule de l'epreuve",
        r"^session \d{4}$",
        r"^dnb serie generale page \d+/\d+",
        r"^dnb serie generale page \d+ sur \d+",
        r"^epreuve d'?histoire geographie",
        r"^histoire-geographie$",
        r"^histoire-geographie enseignement moral et civique$",
        r"^enseignement moral et civique$",
        r"^serie generale$",
        r"^duree de l'epreuve",
        r"^duree de l epreuve",
        r"^duree de l'?epreuve.*points$",
        r"^50 points$",
        r"^des que le sujet vous est remis",
        r"^ce sujet comporte",
        r"^attention",
        r"^cette page doit etre",
        r"^annexe.*rendre avec la copie",
        r"^annexe.*est a rendre avec la copie",
        r"^annexe page \d+/\d+.*rendre",
        r"^a placer a l'interieur",
        r"^cette feuille doit etre detachee",
        r"^votre copie double$",
        r"^afin de respecter l'anonymat",
        r"^citer votre nom",
        r"^l'utilisation du dictionnaire",
        r"^l utilisation du dictionnaire",
        r"^l.?utilisation du dictionnaire",
        r"^ne rien ecrire",
        r"^ne pas inscrire",
        r"^de signe distinctif",
        r"^votre reponse ne comportera aucun element d'identite",
        r"^page \d+/\d+$",
        r"^page \d+ sur \d+$",
        r"^dnb serie generale$",
        r"^\d{2}-?genhgemc[a-z0-9-]*$",
        r"^\d{2}-?genhgemc[a-z0-9-]*\s+page agrandie.*$",
        r"^page agrandie \d+\s*/\s*\d+.*$",
    ]

    return any(re.search(pattern, compact) for pattern in patterns)


def clean_subject_text(text):
    lines = [line.strip() for line in text.splitlines()]
    cleaned = []
    started = False
    skip_following_anonymity = False

    for line in lines:
        normalized = normalize_for_match(line)

        if not started:
            if re.match(r"^exercice\s+\d+", normalized):
                started = True
            else:
                continue

        if "afin de respecter" in normalized:
            skip_following_anonymity = True
            continue

        if skip_following_anonymity:
            if "etablissement" in normalized or not line:
                skip_following_anonymity = False
            continue

        if is_boilerplate_line(line):
            continue

        cleaned.append(line)

    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_known_inline_noise(markdown):
    patterns = [
        r"\n\(DROM/COM\)\n",
        r"\s+50 activités en Géographie au cycle 3, juin 2014\.",
    ]
    for pattern in patterns:
        markdown = re.sub(pattern, "\n", markdown, flags=re.IGNORECASE)

    markdown = re.sub(
        r"https://www\.reseau-canope\.fr/50-activites-en-\s+geographie-au-cycle3/document31\.html",
        "https://www.reseau-canope.fr/50-activites-en-geographie-au-cycle3/document31.html",
        markdown,
        flags=re.IGNORECASE,
    )
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def remove_exercise_summary(markdown):
    lines = markdown.splitlines()
    cleaned = []
    index = 0

    while index < len(lines):
        stripped = lines[index].strip()
        normalized = normalize_for_match(stripped)

        is_summary_heading = bool(
            re.match(
                r"^##\s+exercice\s+\d+\s*-\s*(?:\(emc\)\s*)?\d+\s*points?\.?$",
                normalized,
            )
        )

        if is_summary_heading:
            index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            continue

        cleaned.append(lines[index])
        index += 1

    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_trailing_appendix_residue(markdown):
    lines = markdown.splitlines()
    cleaned = []

    for line in lines:
        normalized = normalize_for_match(line.strip())
        if re.match(r"^annexe\s+a\s+rendre\b", normalized):
            break
        cleaned.append(line)

    text = "\n".join(cleaned)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_misplaced_tail_residue(markdown):
    patterns = [
        r"\s+Le budget participatif en quelques mots\s*:\s*[\s\S]*?(?=\n\d+\.\s+Sur la frise chronologique|\Z)",
        r"\n1\.\s+Sur la frise chronologique ci-dessous,[\s\S]*?(?=\n## Exercice|\Z)",
        r"\s+Afin de respecter l.anonymat de votre copie,[\s\S]*?(?=\n## Exercice|\Z)",
        r"\n1\.\s+Indiquez le nom de chaque dirigeant dans les encadrés\.[\s\S]*?(?=\n## Exercice|\Z)",
    ]
    for pattern in patterns:
        markdown = re.sub(pattern, "", markdown, flags=re.IGNORECASE)

    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def apply_subject_specific_cleanups(exercise_id, markdown):
    if exercise_id == "dnb-hgemc-2024-am-rique-du-nord-39":
        markdown = markdown.replace(
            """**Document 1 : Témoignages sur la chute du mur de Berlin, le 9 novembre 1989.**

> Source : Hélène Kohl, « Ils ont vécu la chute du mur de Berlin », www.europe1.fr, le 8 novembre 2019.

**Document 2 : La réconciliation allemande en 1990.**

> Source : Plantu, dessin de presse paru dans Le Monde, le 2 février 1990. « Un événement comme ça, ça reste pour toujours dans ta tête ! » Cette nuit -là, comme beaucoup de Berlinois de l’Est, Ursula s’est d’abord rendue au mur pour vérifier la rumeur qui parcourt la ville : il n’y a plus besoin d’autorisation spéciale pour sortir de RDA [= République Démocratique Allemande ], selon une déclaration du porte-parole du régime, faite quelques heures plus tôt à la télévision. En réalité, cet homme s’est trompé en lisant ses notes. Et d’ailleurs, aux postes -frontières, comme celui du pont de Bornholmer, les soldats n’ont reçu aucun ordre. Ils ne savent pas quoi faire. Normalement, ils devraient tirer. « La police est arrivée, elle voulait nous refouler mais on est restés là, sans bouger », raconte Michael à Europe 1. Finalement, en hésitant, un soldat prend l’initiative de lever les barrières. « Rien que de traverser ce pont, c’était un sentiment immense de libération », se souvient Ursula. Michael se retrouve à faire la fête avec des inconnus sur la grande avenue de Berlin Ouest : « Sur l’[avenue] Ku’damm, c’était la folie ! » On rit, on pleure, on s’embrasse, on danse. Henry est comme sidéré : « J’étais juste là, à regarder. Soudain, en une nuit, il était évident que la RDA et le communisme, c’était fini pour toujours. »

Drapeau RDA Drapeau RFA""",
            (
                "**Document 1 : Témoignages sur la chute du mur de Berlin, le 9 novembre 1989.**\n\n"
                "« Un événement comme ça, ça reste pour toujours dans ta tête ! » Cette nuit-là, comme beaucoup de Berlinois de l’Est, Ursula s’est d’abord rendue au mur pour vérifier la rumeur qui parcourt la ville : il n’y a plus besoin d’autorisation spéciale pour sortir de RDA [= République démocratique allemande], selon une déclaration du porte-parole du régime, faite quelques heures plus tôt à la télévision. En réalité, cet homme s’est trompé en lisant ses notes. Et d’ailleurs, aux postes-frontières, comme celui du pont de Bornholmer, les soldats n’ont reçu aucun ordre. Ils ne savent pas quoi faire. Normalement, ils devraient tirer. « La police est arrivée, elle voulait nous refouler mais on est restés là, sans bouger », raconte Michael à Europe 1. Finalement, en hésitant, un soldat prend l’initiative de lever les barrières. « Rien que de traverser ce pont, c’était un sentiment immense de libération », se souvient Ursula. Michael se retrouve à faire la fête avec des inconnus sur la grande avenue de Berlin Ouest : « Sur l’[avenue] Ku’damm, c’était la folie ! » On rit, on pleure, on s’embrasse, on danse. Henry est comme sidéré : « J’étais juste là, à regarder. Soudain, en une nuit, il était évident que la RDA et le communisme, c’était fini pour toujours. »\n\n"
                "> Source : Hélène Kohl, « Ils ont vécu la chute du mur de Berlin », www.europe1.fr, le 8 novembre 2019.\n\n"
                "**Document 2 : La réconciliation allemande en 1990.**\n\n"
                "![Document iconographique](assets/documents/dnb-hgemc-2024-am-rique-du-nord-39-document-crop-page-2.jpg)\n\n"
                "> Source : Plantu, dessin de presse paru dans Le Monde, le 2 février 1990."
            ),
        )
        markdown = markdown.replace(
            '<p class="exercise-part-title question-title"><span>?</span>Questions</p>',
            '<p class="exercise-part-title question-title"><span>?</span>Questions <small>(20 points)</small></p>',
            1,
        )
        markdown = markdown.replace(
            """## Exercice 2 - : MAÎTRISER DIFFÉRENTS LANGAGES POUR RAISONNER ET

UTILISER DES REPÈRES GEOGRAPHIQUES. (20 POINTS)""",
            "## Exercice 2 - : MAÎTRISER DIFFÉRENTS LANGAGES POUR RAISONNER (20 POINTS)",
        )
        markdown = markdown.replace(
            "2. Se repérer dans l’espace. (6 points)",
            '<p class="exercise-part-title"><span>2</span>Se repérer dans l’espace <small>(6 points)</small></p>',
        )
        markdown = markdown.replace(
            """## Exercice 3 - : MOBILISER DES COMPÉTENCES RELEVANT DE

L'ENSEIGNEMENT MORAL ET CIVIQUE. (10 POINTS)""",
            "## Exercice 3 - : MOBILISER DES COMPÉTENCES RELEVANT DE L'ENSEIGNEMENT MORAL ET CIVIQUE. (10 POINTS)",
        )
        markdown = markdown.replace(
            """**Document 1 : Le SNU organisé dans les Pyrénées-Orientales.**

> Source : Maïté Torres, « Service National Universel. Retour d’expérience dans les Pyrénées-Orientales », https://madeinperpignan.com/service-national- universel-obligatoire-retour-experience-temoignages-pyrenees-orientales/, le 9 janvier 2023.

1 : Centre d’entraînement de l’armée.

**Document 2 : Extraits du dépliant 2023 du SNU.**""",
            (
                "**Document 1 : Le SNU organisé dans les Pyrénées-Orientales.**\n\n"
                "![Document iconographique](assets/documents/dnb-hgemc-2024-am-rique-du-nord-39-document-crop-page-5-doc1.jpg)\n\n"
                "> Source : Maïté Torres, « Service National Universel. Retour d’expérience dans les Pyrénées-Orientales », https://madeinperpignan.com/service-national-universel-obligatoire-retour-experience-temoignages-pyrenees-orientales/, le 9 janvier 2023.\n\n"
                "1 : Centre d’entraînement de l’armée.\n\n"
                "**Document 2 : Extraits du dépliant 2023 du SNU.**"
            ),
        )
        markdown = markdown.replace(
            """**Document 2 : Extraits du dépliant 2023 du SNU.**

> Source : www.snu.gouv.fr Pour les jeunes accueillis dans les Pyrénées -Orientales, le programme prévoit – outre des activités sportives, randonnée en montagne, balade en raquette – une initiation aux gestes de premier s secours, ou l’éducation musicale ou à l’environnement. C’est auss i l’occasion de former aux valeurs patriotiques avec levée des couleurs chaque matin, une journée dédiée à la défense de la mémoire et une visite du centre commando de Mont -Louis1. Guillaume Stoecklin, chef du Service départemental à la jeunesse, à l’enga gement et aux sports (SDJE S) des Pyrénées-Orientales évoque les 9 thèmes abordés, de la pratique sportive à la connaissance des institutions, en passant par l’engagement personnel sous différentes formes (associatif, militaire…). […] « Par exemple, un matin , dans le cadre de l’apprentissage des gestes de sécurité, ils vont apprendre à donner l’alerte en cas d’accident de la route ; et l’après -midi, ils vont faire une randonnée. Avec un accompagnateur de montagne, ils seront sensibilisés à la faune et la flor e locales ; le 3e jour, la Banque de France les sensibilise aux risques des arnaques en ligne […] et un maire leur explique ce que fait le Département ou la Préfecture. », précise Guillaume. […]""",
            (
                "**Document 2 : Extraits du dépliant 2023 du SNU.**\n\n"
                "![Document iconographique](assets/documents/dnb-hgemc-2024-am-rique-du-nord-39-document-crop-page-5-doc2.jpg)\n\n"
                "> Source : www.snu.gouv.fr\n"
            ),
        )

    if exercise_id == "dnb-hgemc-2025-liban-52":
        markdown = re.sub(
            r"\*\*Document 1 : Disneyland Paris, un territoire connecté[\s\S]*?\n\n!\[Document iconographique\]\(assets/documents/dnb-hgemc-2025-liban-52-document-crop-page-2\.jpg\)",
            "**Document 1 : Disneyland Paris, un territoire connecté**\n\n![Document iconographique](assets/documents/dnb-hgemc-2025-liban-52-document-crop-page-2.jpg)",
            markdown,
            flags=re.IGNORECASE,
        )

        markdown = re.sub(
            r"\*\*Document 2 : Le projet Disneyland Paris : un projet stratégique, en constante évolution Disneyland Paris est la première destination touristique d’Europe avec deux parcs à thème\*\*",
            "**Document 2 : Le projet Disneyland Paris : un projet stratégique, en constante évolution**\n\nDisneyland Paris est la première destination touristique d’Europe avec deux parcs à thème",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(r"\s+\b(5|10|15|20|25)\b\s+", " ", markdown)
        markdown = markdown.replace("", "- ")
        markdown = markdown.replace("assure 000 emplois directs", "assure 15 000 emplois directs")
        markdown = markdown.replace("prefectures-regions.g ouv.fr", "prefectures-regions.gouv.fr")
        markdown = markdown.replace(
            "ainsi que le\n\n(1) Régie Autonome des Transports Parisiens: Société qui gère les transports en commun d’Île-de-France.\n\ndéveloppement d’une agglomération",
            "ainsi que le développement d’une agglomération",
        )
        markdown = markdown.replace(
            "\n\n> Source : D’après prefectures-regions.gouv.fr, 24 décembre 2019, consulté le 19/12/2024.",
            "\n\n(1) Régie Autonome des Transports Parisiens : société qui gère les transports en commun d’Île-de-France.\n\n> Source : D’après prefectures-regions.gouv.fr, 24 décembre 2019, consulté le 19/12/2024.",
        )
        markdown = markdown.replace(
            '<p class="exercise-part-title question-title"><span>?</span>Questions</p>',
            '<p class="exercise-part-title question-title"><span>?</span>Questions <small>(20 points)</small></p>',
            1,
        )

        markdown = re.sub(
            r"\n<p class=\"exercise-part-title\"><span>2</span>Comprendre et pratiquer un autre langage ; utiliser des repères historiques <small>\(3 pts\)</small></p>[\s\S]*?(?=\n## Exercice 3|\Z)",
            (
                '\n<p class="exercise-part-title"><span>2</span>Comprendre et pratiquer un autre langage ; utiliser des repères historiques <small>(3 pts)</small></p>\n\n'
                '![Document iconographique](assets/documents/dnb-hgemc-2025-liban-52-document-crop-page-6.jpg)\n'
            ),
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(
            r"\*\*Document 1 : L’usage positif d’un réseau social, Booktok BookTok est une communauté de tiktokeurs qui postent des vidéos où ils partagent leur amour des livres et de la lecture\.\*\*\s*",
            "**Document 1 : L’usage positif d’un réseau social, Booktok**\n\nBookTok est une communauté de tiktokeurs qui postent des vidéos où ils partagent leur amour des livres et de la lecture. ",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(
            r"\*\*Document 2 : Lutter contre le cyberharcèlement Partager des images à caractère sexuel d’une personne sans son\*\*\s*consentement est passible de deux ans de prison et 60 000 euros d’amende\.\s*\n\s*\nCampagne de sensibilisation pour lutter contre le harcèlement à l’école,\s*\n> Source : https://www\.education\.gouv\.fr\s*\n\s*Une photo c’est perso, la partager c’est harceler POUR L’ÉCOLE DE LA CONFIANCE NON AU HARCÈLEMENT NonAuHarcelement\.education\.gouv\.fr – #NonAuHarcelement 3020 Service & appel gratuits\s*\n\s*!\[Document iconographique\]\(assets/documents/dnb-hgemc-2025-liban-52-document-crop-page-9\.jpg\)",
            "**Document 2 : Lutter contre le cyberharcèlement**\n\n> Source : https://www.education.gouv.fr\n\n![Document iconographique](assets/documents/dnb-hgemc-2025-liban-52-document-crop-page-9.jpg)",
            markdown,
            flags=re.IGNORECASE,
        )

    if exercise_id == "dnb-hgemc-2025-m-tropole-47":
        markdown = re.sub(
            r"\*\*Document 2 : La création d’ un terminal de croisière à Papeete \(Polynésie\*\*\s*\n\s*française\)",
            "**Document 2 : La création d’ un terminal de croisière à Papeete (Polynésie française)**",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(
            r"\*\*Document 1 : Marseille célèbre la journée de l’Europe \(2023\) Chaque année, le 9 mai, la Journée de l ’Europe célèbre la paix et l’unité en Europe\.\*\*\s*",
            "**Document 1 : Marseille célèbre la journée de l’Europe (2023)**\n\nChaque année, le 9 mai, la Journée de l ’Europe célèbre la paix et l’unité en Europe. ",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(
            r"\nConsigne a\) Complétez le tableau suivant\s*:\s*[\s\S]*?(?=\Z)",
            "",
            markdown,
            flags=re.IGNORECASE,
        )

    if exercise_id == "dnb-hgemc-2025-m-tropole-53":
        markdown = re.sub(
            r"\*\*Document 1 : La région Hauts-de-France devient la « vallée de la batterie » L’annonce ce mardi de l ’implantation à Dunkerque d’ une troisième gigafactory de\*\*\s*",
            "**Document 1 : La région Hauts-de-France devient la « vallée de la batterie »**\n\nL’annonce ce mardi de l ’implantation à Dunkerque d’ une troisième gigafactory de ",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(
            r"### Annexe à compléter\s*\n\s*!\[Annexe à compléter\]\(assets/annexes/dnb-hgemc-2025-m-tropole-53-annexe-page-4\.jpg\)\s*\n\s*!\[Annexe à compléter\]\(assets/annexes/dnb-hgemc-2025-m-tropole-53-annexe-page-7\.jpg\)",
            "### Annexe à compléter\n\n![Annexe à compléter](assets/annexes/dnb-hgemc-2025-m-tropole-53-annexe-page-7.jpg)",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(
            r"\*\*Document 2 : Extrait de la Constitution de la Ve République ARTICLE PREMIER\*\*\s*La France est une République indivisible, laïque, démocratique et sociale\.[\s\S]*?> Source : site du Conseil constitutionnel\s*\n\s*!\[Document iconographique\]\(assets/documents/dnb-hgemc-2025-m-tropole-53-document-crop-page-6\.jpg\)",
            "**Document 2 : Extrait de la Constitution de la Ve République**\n\nARTICLE PREMIER\n\nLa France est une République indivisible, laïque, démocratique et sociale. Elle assure l'égalité devant la loi de tous les citoyens sans distinction d'origine, de race ou de religion. Elle respecte toutes les croyances. Son organisation est décentralisée. La loi favorise l'égal accès des femmes et des hommes aux mandats électoraux et fonctions électives, ainsi qu'aux responsabilités professionnelles et sociales.\n\n> Source : site du Conseil constitutionnel",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(
            r"\nConsigne:\s*À travers des pièces, la Monnaie de Paris commémore des évènements historiques majeurs après 1945\.[\s\S]*?(?=\Z)",
            "",
            markdown,
            flags=re.IGNORECASE,
        )

    if exercise_id == "dnb-hgemc-2025-pays-du-groupe-1-55":
        markdown = re.sub(
            r"\s*L[’']utilisation du dictionnaire et de la calculatrice est interdite\.\s*",
            "\n",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = markdown.replace(
            "https://www.touteleurope.eu/fonctionnement-de-l-ue/qu-est-ce-que-la-citoyennete-de-l-union- europeenne/",
            "https://www.touteleurope.eu/fonctionnement-de-l-ue/qu-est-ce-que-la-citoyennete-de-l-union-europeenne/",
        )
        markdown = re.sub(
            r"\*\*Document 2 : Erasmus\+, un programme de l'Union européenne destiné à soutenir\*\*\s*\n\s*l'éducation, la formation, la jeunesse et le sport en Europe",
            "**Document 2 : Erasmus+, un programme de l'Union européenne destiné à soutenir l'éducation, la formation, la jeunesse et le sport en Europe**",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(
            r"\nLa France métropolitaine[\s\S]*?(?=\Z)",
            "",
            markdown,
            flags=re.IGNORECASE,
        )

    if exercise_id == "dnb-hgemc-2025-polyn-sie-fran-aise-56":
        markdown = re.sub(
            r"\nDémocraties fragilisées et expériences totalitaires dans l’Europe de l’entre-deux guerres\.\n",
            "\n",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = markdown.replace(
            "**Document 1 : Incendie du Reichstag (siège du parlement à Berlin), 27 février 1933.**\n\n**Document 2 :",
            (
                "**Document 1 : Incendie du Reichstag (siège du parlement à Berlin), 27 février 1933.**\n\n"
                "![Document iconographique](assets/documents/dnb-hgemc-2025-polyn-sie-fran-aise-56-document-crop-page-2-photo.jpg)\n\n"
                "Le Reichstag est le siège du parlement allemand, où les lois sont votées démocratiquement. "
                "Les nazis prennent prétexte de l’incendie du Reichstag, qu’ils attribuent abusivement à un déséquilibré, "
                "membre du parti communiste, pour interdire ce dernier et abolir les libertés civiles.\n\n"
                "> Source : Photo prise le 27 février 1933, auteur inconnu\n\n"
                "**Document 2 :"
            ),
        )
        markdown = markdown.replace(
            "Légiférer1 : faire des lois Un train2 : une série Omnipotent3 : tout puissant\n\nLe Reichstag est le siège du parlement allemand, où les lois sont votées démocratiquement. Les nazis prennent prétexte de l’incendie du Reichstag, qu’ils attribuent abusivement à un déséquilibré, membre du parti communiste, pour interdire ce dernier et abolir les libertés civiles.\n\n> Source : Photo prise le 27 février 1933, auteur inconnu",
            "Légiférer1 : faire des lois Un train2 : une série Omnipotent3 : tout puissant",
        )
        markdown = markdown.replace(
            "1. Sous la forme d ’un développement construit d ’une vingtaine de lignes et en vous appuyant sur une étude de cas ou sur des exemples vus en classe, décrivez les différents espaces d’une aire urbaine et expliquez leurs dynamiques. (14 points)",
            (
                '<p class="exercise-part-title"><span>1</span>Développement construit <small>(14 points)</small></p>\n\n'
                "Sous la forme d’un développement construit d’une vingtaine de lignes et en vous appuyant sur une étude de cas ou sur des exemples vus en classe, décrivez les différents espaces d’une aire urbaine et expliquez leurs dynamiques."
            ),
        )
        markdown = markdown.replace(
            "2. Complétez l’annexe à la page 7/7. (6 points)",
            (
                '<p class="exercise-part-title"><span>2</span>Différents langages <small>(6 points)</small></p>\n\n'
                "Complétez l’annexe à la page 7/7."
            ),
        )
        markdown = markdown.replace(
            "Thème : Construire une culture civique Expliquer le lien entre l’engagement et la responsabilité",
            "### Thème : Construire une culture civique - Expliquer le lien entre l’engagement et la responsabilité",
        )
        markdown = re.sub(
            r"\*\*Document 1 : Alerte tsunami, les élèves de Tahaa jouent le jeu Quels sont les bons gestes à adopter face à un tsunami \? Nul ne doute que les\*\*\s*\n\s*enfants de Tahaa les connaissent désormais par cœur, à l\s*[’']issue de l\s*[’']exercice grandeur nature réalisé au collège de l'île vanille\.",
            (
                "**Document 1 : Alerte tsunami, les élèves de Tahaa jouent le jeu**\n\n"
                "Quels sont les bons gestes à adopter face à un tsunami ? Nul ne doute que les enfants de Tahaa les connaissent désormais par cœur, à l’issue de l’exercice grandeur nature réalisé au collège de l'île vanille."
            ),
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = markdown.replace(
            "**Document 2 : Plan individuel de mise en sûreté (PIMS)**\n\n> Source : Site du Haut-commissariat de Polynésie française, mis à jour le 23/10/2024",
            (
                "**Document 2 : Plan individuel de mise en sûreté (PIMS)**\n\n"
                "> Source : Site du Haut-commissariat de Polynésie française, mis à jour le 23/10/2024\n\n"
                "![Document iconographique](assets/documents/dnb-hgemc-2025-polyn-sie-fran-aise-56-document-crop-page-5.jpg)"
            ),
        )
        markdown = re.sub(
            r"\n\n- Nommez et localisez la Polynésie française et la Nouvelle Calédonie\.\n- Nommez et localisez l’Afrique\.\n- Nommez et localisez la France métropolitaine\.\n- Nommez et localisez l’océan Pacifique et l’océan Indien\.\s*\Z",
            "",
            markdown,
        )

    if exercise_id == "dnb-hgemc-2025-nouvelle-cal-donie-54":
        markdown = markdown.replace(
            '<p class="exercise-part-title question-title"><span>?</span>Questions</p>',
            '<p class="exercise-part-title question-title"><span>?</span>Questions <small>(20 points)</small></p>',
            1,
        )
        markdown = re.sub(
            r"## Exercice 2 - MAÎTRISER DIFFÉRENTS LANGAGES POUR RAISONNER ET SE REPÉRER \(20 points\)\s*\n\s*### HISTOIRE – L’Europe, un théâtre majeur des guerres totales \(1914 -1945\) : la Seconde\s*\n\s*Guerre mondiale, une guerre d’anéantissement\s*\n\s*1\. Sous la forme d’un développement construit d’une vingtaine de lignes et en vous appuyant sur des exemples étudiés en classe, vous montrerez que la Seconde Guerre mondiale est une guerre d’anéantissement\. \(13 points\)\s*\n\s*2\. Sur l’annexe, page 7 sur 7, à rendre avec votre copie\. \(7 points\)\s*\n\s*- Pour chaque événement A, B et C, indiquez l’année qui lui correspond\. \(3 points\)\s*\n\s*- Reportez les lettres des trois événements sur la frise chronologique en les écrivant dans les cercles\. \(3 points\)\s*\n\s*- Complétez la légende en nommant les deux périodes repérées sur la frise\. \(1 point\)\s*\n\s*### Annexe à compléter\s*\n\s*!\[Annexe à compléter\]\(assets/annexes/dnb-hgemc-2025-nouvelle-cal-donie-54-annexe-page-4\.jpg\)\s*\n\s*!\[Annexe à compléter\]\(assets/annexes/dnb-hgemc-2025-nouvelle-cal-donie-54-annexe-page-7\.jpg\)",
            "## Exercice 2 - MAÎTRISER DIFFÉRENTS LANGAGES POUR RAISONNER ET SE REPÉRER (20 points)\n\n### HISTOIRE – L’Europe, un théâtre majeur des guerres totales (1914 -1945) : la Seconde Guerre mondiale, une guerre d’anéantissement\n\n<p class=\"exercise-part-title\"><span>1</span>Développement construit <small>(13 points)</small></p>\n\nSous la forme d’un développement construit d’une vingtaine de lignes et en vous appuyant sur des exemples étudiés en classe, vous montrerez que la Seconde Guerre mondiale est une guerre d’anéantissement.\n\n<p class=\"exercise-part-title\"><span>2</span>Maîtrise différents langages <small>(7 points)</small></p>\n\n### Annexe à compléter\n\n![Annexe à compléter](assets/annexes/dnb-hgemc-2025-nouvelle-cal-donie-54-annexe-page-7.jpg)",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(
            r"\*\*Document 1\. Qu’est-ce qu’une discrimination \? Je m’appelle Dimitri, j’ai 23 ans, je suis JADE, c’est l’acronyme de Jeune Ambassadeur des\*\*\s*",
            "**Document 1. Qu’est-ce qu’une discrimination ?**\n\nJe m’appelle Dimitri, j’ai 23 ans, je suis JADE, c’est l’acronyme de Jeune Ambassadeur des ",
            markdown,
            flags=re.IGNORECASE,
        )
        markdown = re.sub(
            r"\nFace au droit, nous sommes tous égaux\.[\s\S]*?(?=\Z)",
            "",
            markdown,
            flags=re.IGNORECASE,
        )

    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def exercise_part_heading(line):
    match = re.match(
        r"^([12])\s*[\.\-)\u2013\u2014]\s*(développement construit|developpement construit|comprendre et pratiquer un autre langage[^.]*|repères? historiques?[^.]*|reperes? historiques?[^.]*|repères? géographiques?[^.]*|reperes? geographiques?[^.]*)\.?\s*(.*)$",
        line,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    number = match.group(1)
    title = " ".join(match.group(2).split()).rstrip(" .")
    rest = " ".join(match.group(3).split()).strip()

    points_match = re.search(r"(\(\s*\d+\s*points?\s*\)|\(\s*\d+\s*pts?\s*\))$", title, flags=re.IGNORECASE)
    points = ""
    if points_match:
        points = points_match.group(1)
        title = title[: points_match.start()].strip()
    elif re.fullmatch(r"\(\s*\d+\s*points?\s*\)|\(\s*\d+\s*pts?\s*\)", rest, flags=re.IGNORECASE):
        points = rest
        rest = ""

    title = re.sub(r"^developpement", "Développement", title, flags=re.IGNORECASE)
    title = re.sub(r"^reperes", "Repères", title, flags=re.IGNORECASE)
    title = re.sub(r"geographiques", "géographiques", title, flags=re.IGNORECASE)
    title = re.sub(r"historiques", "historiques", title, flags=re.IGNORECASE)
    points_html = f" <small>{html.escape(points)}</small>" if points else ""
    heading = f'<p class="exercise-part-title"><span>{number}</span>{html.escape(title)}{points_html}</p>'

    return heading, rest


def merge_exercise_part_continuations(markdown):
    split_title_pattern = re.compile(
        r'(<p class="exercise-part-title"><span>(?P<number>[12])</span>(?P<title>[^<]*?repères?)</p>)\n\n(?P<rest>(?:historiques?|géographiques?|geographiques?)[^\n]*)',
        flags=re.IGNORECASE,
    )

    def replace_split_title(match):
        title = f"{match.group('title')} {match.group('rest')}".strip()
        points = ""
        points_match = re.search(r"(\(\s*\d+\s*points?\s*\)|\(\s*\d+\s*pts?\s*\))", title, flags=re.IGNORECASE)
        if points_match:
            points = points_match.group(1)
            title = f"{title[:points_match.start()]} {title[points_match.end():]}".strip()
        title = title.rstrip(" .")
        title = re.sub(r"\s+", " ", title)
        points_html = f" <small>{html.escape(points)}</small>" if points else ""
        return f'<p class="exercise-part-title"><span>{match.group("number")}</span>{html.escape(title)}{points_html}</p>'

    markdown = split_title_pattern.sub(replace_split_title, markdown)

    isolated_points_pattern = re.compile(
        r'(<p class="exercise-part-title"><span>(?P<number>[12])</span>(?P<title>[^<]*?)</p>)\n\n(?P<points>\(\s*\d+\s*(?:points?|pts?)\s*\))',
        flags=re.IGNORECASE,
    )

    def replace_isolated_points(match):
        return (
            f'<p class="exercise-part-title"><span>{match.group("number")}</span>'
            f'{match.group("title").strip()} <small>{html.escape(match.group("points"))}</small></p>'
        )

    markdown = isolated_points_pattern.sub(replace_isolated_points, markdown)

    repere_instruction_points_pattern = re.compile(
        r'(<p class="exercise-part-title"><span>(?P<number>[12])</span>(?P<title>[^<]*(?:repères?|langage)[^<]*?)</p>)\n\n'
        r'(?P<instruction>[^\n]*?)(?P<points>\(\s*\d+\s*(?:points?|pts?)\s*\))(?P<after>[^\n]*)',
        flags=re.IGNORECASE,
    )

    def replace_repere_instruction_points(match):
        instruction = f"{match.group('instruction')}{match.group('after')}".strip()
        instruction = re.sub(r"\s+([.])$", r"\1", instruction)
        return (
            f'<p class="exercise-part-title"><span>{match.group("number")}</span>'
            f'{match.group("title").strip()} <small>{html.escape(match.group("points"))}</small></p>'
            f'\n\n{instruction}'
        )

    markdown = repere_instruction_points_pattern.sub(replace_repere_instruction_points, markdown)

    development_instruction_points_pattern = re.compile(
        r'(?P<heading><p class="exercise-part-title"><span>(?P<number>1)</span>(?P<title>Développement construit)</p>)\n\n'
        r'(?P<chapter>### [^\n]+\n\n)?'
        r'(?P<instruction>(?:Rédigez|Redigez|Sous la forme)[^\n]*?)(?P<points>\(\s*\d+\s*(?:points?|pts?)\s*\))(?P<after>[^\n]*)',
        flags=re.IGNORECASE,
    )

    def replace_development_instruction_points(match):
        heading = (
            f'<p class="exercise-part-title"><span>{match.group("number")}</span>'
            f'{match.group("title").strip()} <small>{html.escape(match.group("points"))}</small></p>'
        )
        instruction = f"{match.group('instruction')}{match.group('after')}".strip()
        instruction = re.sub(r"\s+([.])$", r"\1", instruction)
        chapter = match.group("chapter") or ""
        return f"{chapter}{heading}\n\n{instruction}"

    return development_instruction_points_pattern.sub(replace_development_instruction_points, markdown)


def merge_document_title_continuations(markdown):
    lines = markdown.splitlines()
    output = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if (
            re.match(r"^\*\*Document\s+\d+\b.*\*\*$", line.strip(), flags=re.IGNORECASE)
            and index + 2 < len(lines)
            and not lines[index + 1].strip()
        ):
            continuation = lines[index + 2].strip()
            normalized = normalize_for_match(continuation)
            title_normalized = normalize_for_match(line.strip()[:-2].rstrip())
            title_expects_continuation = bool(
                re.search(r"(?:\bde|\bdu|\bdes|\bau|\baux|\bla|\ble|lors de|contre le)$", title_normalized)
            )
            if (
                continuation
                and len(continuation) <= 90
                and not is_markdown_block_start(continuation)
                and not normalized.startswith("source")
                and (
                    re.match(r"^[A-ZÉÈÀÂÎÏÔÙÛÇ]", continuation)
                    or title_expects_continuation
                )
            ):
                title = line.strip()[:-2].rstrip()
                if "." in continuation:
                    end_index = continuation.find(".") + 1
                    title_continuation = continuation[:end_index].strip()
                    rest = continuation[end_index:].strip()
                else:
                    title_continuation = continuation
                    rest = ""

                output.append(f"{title} {title_continuation}**")
                if rest:
                    output.extend(["", rest])
                index += 3
                continue

        output.append(line)
        index += 1

    return "\n".join(output)


def join_split_document_titles(markdown):
    split_bold_pattern = re.compile(
        r"(\*\*Document\s+\d+\s*:\s*[^\n*]+?)\n([^\n*][^\n]*\*\*)",
        flags=re.IGNORECASE,
    )

    def replace_split_bold(match):
        first = match.group(1).rstrip()
        second = match.group(2).lstrip()
        return f"{first} {second}"

    markdown = split_bold_pattern.sub(replace_split_bold, markdown)

    trailing_bold_pattern = re.compile(
        r"(\*\*Document\s+\d+\s*:\s*[^\n*]+?)\*\*\n([A-ZÉÈÀÂÎÏÔÙÛÇa-z][^\n]*\.)",
        flags=re.IGNORECASE,
    )

    def replace_trailing_bold(match):
        first = match.group(1).rstrip()
        second = match.group(2).strip()
        return f"{first} {second}**"

    return trailing_bold_pattern.sub(replace_trailing_bold, markdown)


def is_appendix_page(page_text, page_index, page_count):
    normalized = normalize_for_match(page_text)
    compact = re.sub(r"\s+", " ", normalized)

    if page_index < max(0, page_count - 4):
        return False

    has_appendix_signal = any(
        signal in compact
        for signal in [
            "annexe",
            "fond de carte",
            "frise chronologique",
            "legende",
        ]
    )
    has_completion_signal = any(
        signal in compact
        for signal in [
            "completez",
            "coloriez",
            "localisez",
            "nommez",
            "situez",
            "representez",
            "a rendre",
        ]
    )

    return has_appendix_signal and has_completion_signal


def render_pdf_page(pdf_path, output_dir, output_name, page_number):
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{output_name}.jpg"
    if output.exists():
        return output.relative_to(ROOT).as_posix()
    if os.environ.get("SKIP_ASSET_RENDER") == "1":
        return ""

    pdftoppm = POPPLER_PATH / "pdftoppm"
    if not pdftoppm.exists():
        return ""

    prefix = output_dir / output_name
    try:
        subprocess.run(
            [
                str(pdftoppm),
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                "-jpeg",
                "-r",
                "145",
                str(pdf_path),
                str(prefix),
            ],
            check=True,
            timeout=90,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""

    generated_candidates = sorted(output_dir.glob(f"{prefix.name}-*.jpg"))
    generated = generated_candidates[-1] if generated_candidates else None
    if generated and generated.exists():
        generated.replace(output)

    return output.relative_to(ROOT).as_posix() if output.exists() else ""


def pdf_words_for_page(pdf_path, page_number):
    pdftotext = POPPLER_FULL_PATH / "pdftotext"
    if not pdftotext.exists():
        return [], None

    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "page.html"
        try:
            subprocess.run(
                [
                    str(pdftotext),
                    "-f",
                    str(page_number),
                    "-l",
                    str(page_number),
                    "-bbox",
                    str(pdf_path),
                    str(output),
                ],
                check=True,
                timeout=20,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return [], None

        root = ET.parse(output).getroot()
        page = root.find(".//{http://www.w3.org/1999/xhtml}page")
        if page is None:
            return [], None

        page_size = {
            "width": float(page.attrib.get("width", 0)),
            "height": float(page.attrib.get("height", 0)),
        }
        words = []
        for word in page.findall("{http://www.w3.org/1999/xhtml}word"):
            words.append(
                {
                    "text": word.text or "",
                    "xMin": float(word.attrib["xMin"]),
                    "yMin": float(word.attrib["yMin"]),
                    "xMax": float(word.attrib["xMax"]),
                    "yMax": float(word.attrib["yMax"]),
                }
            )

        return words, page_size


def text_lines_from_words(words):
    lines = []
    for word in words:
        placed = False
        for line in lines:
            if abs(line["y"] - word["yMin"]) < 4:
                line["words"].append(word)
                line["y"] = min(line["y"], word["yMin"])
                placed = True
                break
        if not placed:
            lines.append({"y": word["yMin"], "words": [word]})

    output = []
    for line in sorted(lines, key=lambda item: item["y"]):
        line_words = sorted(line["words"], key=lambda item: item["xMin"])
        text = " ".join(word["text"] for word in line_words)
        output.append(
            {
                "text": text,
                "xMin": min(word["xMin"] for word in line_words),
                "xMax": max(word["xMax"] for word in line_words),
                "yMin": min(word["yMin"] for word in line_words),
                "yMax": max(word["yMax"] for word in line_words),
            }
        )

    return output


def iconographic_crop_box(pdf_path, page_number):
    words, page_size = pdf_words_for_page(pdf_path, page_number)
    if not words or not page_size:
        return None

    lines = text_lines_from_words(words)
    document_indexes = [
        index
        for index, line in enumerate(lines)
        if re.search(r"\bdocument(?:\s+\d+)?\s*[:.]", normalize_for_match(line["text"]))
    ]
    if not document_indexes:
        return None

    doc_index = document_indexes[0]
    source_index = None
    for index in range(doc_index + 1, len(lines)):
        normalized = normalize_for_match(lines[index]["text"])
        if normalized.startswith("source"):
            source_index = index
            break
        if normalized.startswith("questions") or re.match(r"\bdocument(?:\s+\d+)?\s*[:.]", normalized):
            break

    if source_index is None:
        return None

    y_min = max(0, lines[doc_index]["yMin"] - 8)
    y_max = min(page_size["height"], lines[source_index]["yMax"] + 10)
    if y_max - y_min < 70:
        return None

    return {
        "xMin": 24,
        "xMax": page_size["width"] - 24,
        "yMin": y_min,
        "yMax": y_max,
        "pageWidth": page_size["width"],
        "pageHeight": page_size["height"],
    }


def crop_rendered_pdf_page(image_path, crop_box):
    if not crop_box:
        return False

    path = ROOT / image_path
    if not path.exists():
        return False

    with Image.open(path) as image:
        scale_x = image.width / crop_box["pageWidth"]
        scale_y = image.height / crop_box["pageHeight"]
        box = (
            max(0, int(crop_box["xMin"] * scale_x)),
            max(0, int(crop_box["yMin"] * scale_y)),
            min(image.width, int(crop_box["xMax"] * scale_x)),
            min(image.height, int(crop_box["yMax"] * scale_y)),
        )
        if box[2] <= box[0] or box[3] <= box[1]:
            return False
        image.crop(box).save(path, "JPEG", quality=90, optimize=True)

    return True


def render_appendix_images(exercise_id, pdf_path):
    try:
        pages = read_pdf_pages(pdf_path)
    except Exception:
        return []

    page_count = len(pages)
    page_numbers = [
        index + 1
        for index, page_text in enumerate(pages)
        if is_appendix_page(page_text, index, page_count)
    ]

    if not page_numbers:
        return []

    image_paths = []

    for page_number in page_numbers:
        image_path = render_pdf_page(pdf_path, ANNEX_DIR, f"{exercise_id}-annexe-page-{page_number}", page_number)
        if image_path:
            image_paths.append(image_path)

    return image_paths


def current_exercise_number(page_text):
    normalized = normalize_for_match(page_text)
    matches = list(re.finditer(r"exercice\s+(\d+)", normalized))
    if not matches:
        return None
    return int(matches[-1].group(1))


def is_iconographic_page(page_text, page_index, page_count):
    if is_appendix_page(page_text, page_index, page_count):
        return False

    normalized = normalize_for_match(page_text)
    compact = re.sub(r"\s+", " ", normalized)
    first_document = compact.find("document")
    first_questions = compact.find("questions")

    if first_questions != -1 and (first_document == -1 or first_questions < first_document):
        return False

    has_numbered_document = bool(re.search(r"\bdocument\s+\d+\b", compact))
    has_unnumbered_document = bool(re.search(r"\bdocument\s*[:.]", compact))
    if not has_numbered_document and not has_unnumbered_document:
        return False

    iconographic_signals = [
        "organigramme",
        "schema",
        "instances",
        "democratie participative",
        "photographie",
        "photo ",
        "carte",
        "affiche",
        "infographie",
        "dessin",
        "caricature",
        "croquis",
        "planisphere",
        "graphique",
        "image",
        "logo",
        "tract",
        "une du journal",
    ]
    unnumbered_graphic_signals = [
        "organigramme",
        "instances de la democratie participative",
        "conseil municipal",
        "assemblee communale",
        "ateliers participatifs",
        "groupes actions solutions",
    ]

    if has_unnumbered_document and not has_numbered_document:
        return any(signal in compact for signal in unnumbered_graphic_signals)

    force_iconographic_phrases = [
        "les citoyens votent pour leurs projets preferes a lyon",
        "un atelier de fabrication d'obus en seine-saint-denis en mai 1917",
        "la chanteuse francaise axelle saint-cirel porte le drapeau tricolore",
        "disneyland paris, un territoire connecte",
    ]
    if any(phrase in compact for phrase in force_iconographic_phrases):
        return True

    text_only_signals = [
        "temoignage",
        "extrait",
        "article",
        "discours",
        "lettre",
        "texte",
        "presentation du prix",
    ]

    text_only_phrases = [
        "appel aux femmes francaises de rene viviani, le 7 aout 1914",
        "une presentation du prix",
        "une presentation du prix non au harcelement",
        "le prix non au harcelement a pour objectifs",
        "une puissance diplomatique, militaire et maritime",
        "la guyane : un territoire continental d'outre-mer",
        "les eleves du college revolution de nimes mobilises contre le harcelement scolaire",
        "le projet disneyland paris : un projet strategique, en constante evolution",
    ]
    if any(phrase in compact for phrase in text_only_phrases):
        return False

    has_iconographic_signal = any(signal in compact for signal in iconographic_signals)
    if not has_iconographic_signal:
        return False

    if any(signal in compact for signal in text_only_signals) and not any(signal in compact for signal in ["affiche", "carte", "photographie", "infographie"]):
        return False

    return True


def current_document_number(page_text):
    normalized = normalize_for_match(page_text)
    questions_index = normalized.find("questions")
    if questions_index != -1:
        normalized = normalized[:questions_index]

    matches = list(re.finditer(r"\bdocument\s+(\d+)\b", normalized))
    if not matches:
        return 0 if re.search(r"\bdocument\s*[:.]", normalized) else None
    return int(matches[0].group(1))


def render_iconographic_documents(exercise_id, pdf_path):
    try:
        pages = read_pdf_pages(pdf_path)
    except Exception:
        return {}

    image_paths_by_exercise = {}
    page_count = len(pages)
    active_exercise = None
    active_document = None

    for index, page_text in enumerate(pages):
        number = current_exercise_number(page_text)
        if number:
            active_exercise = number

        document_number = current_document_number(page_text)
        if document_number is not None:
            active_document = document_number

        if not active_exercise or not is_iconographic_page(page_text, index, page_count):
            continue

        page_number = index + 1
        output_name = f"{exercise_id}-document-crop-page-{page_number}"
        output = DOCUMENT_DIR / f"{output_name}.jpg"
        if output.exists():
            image_paths_by_exercise.setdefault(active_exercise, []).append(
                {"document": active_document, "path": output.relative_to(ROOT).as_posix()}
            )
            continue

        image_path = render_pdf_page(
            pdf_path,
            DOCUMENT_DIR,
            output_name,
            page_number,
        )
        if image_path and crop_rendered_pdf_page(image_path, iconographic_crop_box(pdf_path, page_number)):
            image_paths_by_exercise.setdefault(active_exercise, []).append(
                {"document": active_document, "path": image_path}
            )

    return image_paths_by_exercise


def appendix_markdown(image_paths):
    if not image_paths:
        return ""

    images = "\n\n".join(
        f"![Annexe à compléter]({path})"
        for path in image_paths
    )
    return f"\n\n### Annexe à compléter\n\n{images}\n"


def document_images_markdown(assets):
    if not assets:
        return ""

    images = "\n\n".join(
        f"![Document iconographique]({asset['path'] if isinstance(asset, dict) else asset})"
        for asset in assets
    )
    return f"\n\n{images}\n"


def remove_iconographic_duplicate_text(markdown):
    source_tail_starts = [
        "ALLER PLUS LOIN",
        "CONSEIL MUNICIPAL",
        "ASSEMBLEE COMMUNALE",
        "ASSEMBLÉE COMMUNALE",
        "GROUPES ACTIONS",
        "ATELIERS PARTICIPATIFS",
        "HABITANTS VOLONTAIRES",
    ]

    def trim_source_line(line):
        for marker in source_tail_starts:
            index = line.find(marker)
            if index != -1:
                return line[:index].rstrip()
        return line

    def clean_block(match):
        block = match.group(0)
        lines = block.splitlines()
        source_index = next(
            (index for index, line in enumerate(lines) if line.strip().startswith("> Source")),
            None,
        )
        image_index = next(
            (index for index, line in enumerate(lines) if line.strip().startswith("![Document iconographique]")),
            None,
        )

        if source_index is None or image_index is None or image_index <= source_index:
            return block

        is_unnumbered_graphic = bool(re.match(r"^\*\*Document\s*[:.]", lines[0].strip(), flags=re.IGNORECASE))
        if is_unnumbered_graphic:
            title_lines = [line for line in lines[:source_index] if line.strip()]
            source_line = trim_source_line(lines[source_index])
            image_lines = [line for line in lines[image_index:] if line.strip().startswith("![Document iconographique]")]
            return "\n\n".join([*title_lines, source_line, *image_lines])

        cleaned = []
        for index, line in enumerate(lines):
            stripped = line.strip()
            if 1 <= index < source_index and (
                stripped == "."
                or re.match(r"^\d+\.\s+.{1,95}$", stripped)
            ):
                continue
            cleaned.append(line)

        return "\n".join(cleaned)

    pattern = re.compile(
        r"\*\*Document(?:\s+\d+\b|\s*[:.])[\s\S]*?(?=\n\*\*Document(?:\s+\d+\b|\s*[:.])|\n<p class=\"exercise-part-title question-title\"|\n## Exercice|\Z)",
        flags=re.IGNORECASE,
    )
    return pattern.sub(clean_block, markdown)


def inject_exercise_assets(markdown, assets_by_exercise):
    if not assets_by_exercise:
        return markdown

    output = markdown
    for exercise_number in sorted(assets_by_exercise.keys(), reverse=True):
        exercise_assets = assets_by_exercise[exercise_number]
        if not exercise_assets:
            continue

        current_match = None
        for match in re.finditer(rf"(^|\n)##\s+Exercice\s+{exercise_number}\b", output, flags=re.IGNORECASE):
            current_match = match
        next_match = None
        for match in re.finditer(rf"(^|\n)##\s+Exercice\s+{exercise_number + 1}\b", output, flags=re.IGNORECASE):
            next_match = match

        current_index = current_match.start() if current_match else -1
        next_index = next_match.start() if next_match else len(output)
        if current_index != -1 and next_index > current_index:
            section = output[current_index:next_index]
            section_offset = current_index
            inserted_any = False

            for asset in sorted(exercise_assets, key=lambda item: item.get("document") or 99, reverse=True):
                document_number = asset.get("document")
                if document_number is None:
                    continue

                document_match = re.search(
                    (
                        rf"\n\*\*Document\s+{document_number}\b[\s\S]*?(?=\n\*\*Document(?:\s+\d+\b|\s*[:.])|\n<p class=\"exercise-part-title question-title\"|\n\*\*Questions\*\*|\n## Exercice|\Z)"
                        if document_number
                        else r"\n\*\*Document\s*[:.][\s\S]*?(?=\n\*\*Document(?:\s+\d+\b|\s*[:.])|\n<p class=\"exercise-part-title question-title\"|\n\*\*Questions\*\*|\n## Exercice|\Z)"
                    ),
                    section,
                    flags=re.IGNORECASE,
                )
                if not document_match:
                    continue

                insertion = document_images_markdown([asset])
                index = section_offset + document_match.end()
                output = f"{output[:index]}{insertion}{output[index:]}"
                inserted_any = True
                section = output[current_index:next_index + len(insertion)]

            if inserted_any:
                continue

            assets = document_images_markdown(exercise_assets)
            questions_match = re.search(r"\n\*\*Questions\*\*", section)
            if questions_match:
                index = current_index + questions_match.start()
                output = f"{output[:index]}{assets}{output[index:]}"
                continue

        if next_match:
            output = f"{output[:next_match.start()]}{document_images_markdown(exercise_assets)}{output[next_match.start():]}"
        elif current_match:
            output = f"{output.rstrip()}{document_images_markdown(exercise_assets)}"

    return remove_iconographic_duplicate_text(output)


def inject_appendix_markdown(markdown, appendix):
    if not appendix:
        return markdown

    marker = "\n## Exercice 3"
    if marker in markdown:
        index = markdown.rfind(marker)
        return f"{markdown[:index]}{appendix}{markdown[index:]}"

    return f"{markdown.rstrip()}{appendix}"


def is_markdown_block_start(line):
    stripped = line.strip()
    if not stripped:
        return True

    return bool(
        re.match(r"^#{1,6}\s+", stripped)
        or stripped.startswith(">")
        or stripped.startswith("|")
        or re.match(r"^(\*\*Questions\*\*|\*\*Document|\*\*Source)", stripped, flags=re.IGNORECASE)
        or re.match(r"^Documents?\s+\d", stripped, flags=re.IGNORECASE)
        or re.match(r"^[•\-]\s+", stripped)
        or re.match(r"^\d+\s*(?:[\.\-]|/|\))", stripped)
    )


def can_continue_heading(line):
    stripped = line.strip()
    if not stripped or is_markdown_block_start(stripped):
        return False

    return bool(
        stripped[0].islower()
        or stripped.startswith("(")
        or stripped.lower().startswith("points")
        or stripped.lower().startswith("civique")
        or stripped.lower().startswith("moral et civique")
        or stripped.lower().startswith("historiques")
        or stripped.lower().startswith("géographiques")
        or stripped.lower().startswith("geographiques")
        or stripped.lower().startswith("spécifique")
        or stripped.lower().startswith("specifique")
    )


def join_wrapped_markdown(markdown):
    lines = markdown.splitlines()
    joined_headings = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if (
            re.match(r"^#{2,3}\s+", line)
            and index + 2 < len(lines)
            and not lines[index + 1].strip()
            and can_continue_heading(lines[index + 2])
        ):
            joined_headings.append(f"{line.rstrip()} {lines[index + 2].strip()}")
            index += 3
            continue

        joined_headings.append(line)
        index += 1

    output = []
    paragraph = []

    def flush_paragraph():
        if paragraph:
            output.append(" ".join(part.strip() for part in paragraph if part.strip()))
            paragraph.clear()

    for line in joined_headings:
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            if output and output[-1] != "":
                output.append("")
            continue

        if is_markdown_block_start(stripped):
            flush_paragraph()
            output.append(stripped)
            continue

        if output and output[-1] and (
            re.match(r"^\d+\s*(?:[\.\-]|/|\))", output[-1])
            or re.match(r"^[•\-]\s+", output[-1])
            or output[-1].startswith(">")
        ):
            output[-1] = f"{output[-1]} {stripped}"
            continue

        paragraph.append(stripped)

    flush_paragraph()

    text = "\n".join(output)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def markdown_subject_preview(text):
    text = clean_subject_text(text)
    if not text:
        return "Le texte du PDF principal n'a pas pu etre extrait automatiquement."

    lines = text.splitlines()
    markdown = []
    current_exercise_number = ""
    current_exercise_points = ""

    for raw_line in lines:
        line = raw_line.strip().replace("", "-")
        normalized = normalize_for_match(line)

        if not line:
            if markdown and markdown[-1] != "":
                markdown.append("")
            continue

        exercise_match = re.match(r"^exercice\s+(\d+)\.?\s*(.*)$", line, flags=re.IGNORECASE)
        if exercise_match:
            number = exercise_match.group(1)
            rest = exercise_match.group(2).strip()
            title = f"Exercice {number}"
            if rest:
                title += f" - {rest}"
            current_exercise_number = number
            points_match = re.search(r"\(\s*\d+\s*(?:points?|pts?)\s*\)", rest, flags=re.IGNORECASE)
            current_exercise_points = points_match.group(0) if points_match else ""
            if number == "3" and not current_exercise_points:
                current_exercise_points = "(10 points)"
            markdown.extend(["", f"## {title}", ""])
            continue

        if re.match(r"^(histoire|geographie|géographie|emc)\s*[:\-–—]", normalized) and "http" not in normalized and "/" not in line:
            markdown.extend(["", f"### {line}", ""])
            continue

        if normalized.startswith("situation pratique"):
            markdown.extend(["", f"### {line}", ""])
            continue

        if normalized.startswith("document ") or re.match(r"^documents?\s+\d+\s+et\s+\d+", normalized):
            markdown.extend(["", f"**{line}**", ""])
            continue

        if normalized.startswith("questions"):
            points_html = (
                f" <small>{html.escape(current_exercise_points)}</small>"
                if current_exercise_number in {"1", "3"} and current_exercise_points
                else ""
            )
            markdown.extend(["", f'<p class="exercise-part-title question-title"><span>?</span>Questions{points_html}</p>', ""])
            continue

        part_heading = exercise_part_heading(line)
        if part_heading:
            heading, rest = part_heading
            markdown.extend(["", heading, ""])
            if rest:
                markdown.append(rest)
            continue

        if normalized.startswith("source"):
            markdown.append(f"> {line}")
            continue

        if re.match(r"^\d+\.", line):
            markdown.append(line)
            continue

        if re.match(r"^[•\-]\s+", line):
            markdown.append(line)
            continue

        numbered_match = re.match(r"^(?P<number>\d+)\s*(?:[\.\-]|/|\))\s*(?P<body>.*)$", line)
        if numbered_match:
            markdown.append(f"{numbered_match.group('number')}. {numbered_match.group('body').strip()}")
            continue

        markdown.append(line)

    output = "\n".join(markdown)
    output = re.sub(r"\n{3,}", "\n\n", output)
    output = remove_known_inline_noise(output)
    output = merge_exercise_part_continuations(output.strip())
    output = merge_document_title_continuations(output)
    output = join_split_document_titles(output)
    output = remove_exercise_summary(join_wrapped_markdown(output))
    output = remove_trailing_appendix_residue(output)
    return remove_misplaced_tail_residue(output)


def main():
    HTML_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not HTML_PATH.exists():
        subprocess.run(["curl", "-L", "-s", SOURCE_URL, "-o", str(HTML_PATH)], check=True)

    raw_html = HTML_PATH.read_text(encoding="utf-8")
    database = extract_database(raw_html)
    rows = [
        row
        for row in database
        if row.get("discipline") == "Histoire-géographie, EMC"
        and row.get("série") == "Série générale"
    ]

    exercises = []
    PDF_CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = PDF_CACHE
        for index, row in enumerate(rows, 1):
            primary = pick_primary_link(row["links"])
            place = strip_html(row.get("description", ""))
            year_match = re.search(r"\d{4}", row["session"])
            year = int(year_match.group(0)) if year_match else None
            session_kind = row["session"].split(" - ", 1)[1] if " - " in row["session"] else row["session"]
            title = f"{year} - {place} - {session_kind}"
            exercise_id = f"dnb-hgemc-{year}-{slugify(place)}-{index}"
            pdf_path = ensure_pdf_cached(primary["url"], cache_dir) if primary else None
            text = extract_pdf_text(primary["url"], cache_dir) if primary else ""
            exam_code = extract_exam_code(f"{text}\n{primary['url'] if primary else ''}")
            classifications = complete_classifications(text, extract_declared_classifications(text))
            chapters = [item["chapter"] for item in classifications]
            subjects = sorted({item["subject"] for item in classifications if item["subject"] != "À vérifier"})
            if not subjects:
                subjects = infer_subjects(text)
            preview = markdown_subject_preview(text)
            links = [
                {
                    "label": link["label"],
                    "url": link["url"],
                    "kind": "pdf" if link["url"].lower().endswith(".pdf") else "archive",
                }
                for link in row["links"]
            ]
            appendix = appendix_markdown(render_appendix_images(exercise_id, pdf_path)) if pdf_path else ""
            document_assets = render_iconographic_documents(exercise_id, pdf_path) if pdf_path else {}
            extracted_preview = inject_appendix_markdown(
                preview or "Le texte du PDF principal n'a pas pu etre extrait automatiquement.",
                appendix,
            )
            extracted_preview = inject_exercise_assets(extracted_preview, document_assets)
            extracted_preview = merge_exercise_part_continuations(extracted_preview)
            extracted_preview = apply_subject_specific_cleanups(exercise_id, extracted_preview)
            code_markdown = f"**Code épreuve :** `{exam_code}`\n\n" if exam_code else ""

            exercises.append(
                {
                    "id": exercise_id,
                    "subject": "HG-EMC",
                    "subjects": subjects,
                    "chapter": chapters[0],
                    "chapters": chapters,
                    "type": "Sujet complet",
                    "types": infer_types(text),
                    "year": year,
                    "session": row["session"],
                    "place": place,
                    "title": title,
                    "source": "Eduscol",
                    "sourceUrl": SOURCE_URL,
                    "examCode": exam_code,
                    "primaryPdf": primary["url"] if primary else "",
                    "links": links,
                    "keywords": [],
                    "indexedText": clean_subject_text(text)[:18000],
                    "subjectMarkdown": (
                        f"# {title}\n\n"
                        f"{code_markdown}"
                        "<p class=\"cleaned-note\"><strong>Sujet nettoyé.</strong> "
                        "Des erreurs peuvent apparaître par rapport au sujet initial ; "
                        "le PDF officiel reste la référence.</p>\n\n"
                        f"{extracted_preview}"
                    ),
                    "correctionMarkdown": "",
                }
            )

    output = "window.DNB_EXERCISES = "
    output += json.dumps(exercises, ensure_ascii=False, indent=2)
    output += ";\n"
    DATA_PATH.write_text(output, encoding="utf-8")
    DATA_JSON_PATH.write_text(json.dumps(exercises, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(exercises)} sujets HG-EMC série générale écrits dans {DATA_PATH.name}.")


if __name__ == "__main__":
    sys.exit(main())
