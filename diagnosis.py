#things from the notebook. removing prints and unnessary things 

import csv
import math
import re
from collections import Counter

import networkx as nx
from rapidfuzz import fuzz, process

# ---------------------------------------------------------------- 1. creating the triples from the csv files
triples = []

with open("Final CSV.csv", newline="", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    next(reader)  # header
    for row in reader:
        if not row:
            continue
        disease = row[0].strip()
        if not disease:
            continue
        for cell in row[1:]:
            symptom = cell.strip()
            if not symptom:
                continue
            triples.append([disease, "HAS_SYMPTOM", symptom])

with open("final_symptoms_to_disease.csv", newline="", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    next(reader)  # header
    for row in reader:
        disease = row[0].strip()
        symptom_text = row[1].strip()
        for cell in symptom_text.split(","):
            cell = cell.strip()
            if not cell:
                continue
            words = cell.split(" ")
            if "and" in words or "or" in words:
                current_words = []
                for word in words:
                    if word in ("and", "or"):
                        if current_words:
                            triples.append([disease, "HAS_SYMPTOM", " ".join(current_words)])
                            current_words = []
                    else:
                        current_words.append(word)
                if current_words:
                    triples.append([disease, "HAS_SYMPTOM", " ".join(current_words)])
            else:
                triples.append([disease, "HAS_SYMPTOM", cell])

# ---------------------------------------------------------------- 2. creating the graph
G = nx.DiGraph()
for subject, predicate, obj in triples:
    G.add_node(subject, kind="Disease")
    G.add_node(obj, kind="Symptom")
    G.add_edge(subject, obj, relation=predicate)

# ------------------------------------------------- 3. WEIGHTING_1: symptom rarity
symptom_to_diseases = {}
for disease, predicate, symptom in triples:
    symptom_to_diseases.setdefault(symptom, set()).add(disease)

all_diseases = {disease for disease, predicate, symptom in triples}
total_diseases = len(all_diseases)

raw_symptom_weight = {
    symptom: total_diseases / len(diseases)
    for symptom, diseases in symptom_to_diseases.items()
}

_min_weight = min(raw_symptom_weight.values())
_max_weight = max(raw_symptom_weight.values())
_weight_range = _max_weight - _min_weight

symptom_weight = {
    symptom: (weight - 1) * 99 / _weight_range
    for symptom, weight in raw_symptom_weight.items()
}

# --------------------------------------- 4. WEIGHTING_2: symptom-per-disease frequency
disease_rows = Counter()
disease_symptom_rows = {}


def _record_row(disease, symptoms_in_row):
    disease_rows[disease] += 1
    disease_symptom_rows.setdefault(disease, Counter())
    for symptom in symptoms_in_row:
        disease_symptom_rows[disease][symptom] += 1


with open("Final CSV.csv", newline="", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    next(reader)  # header
    for row in reader:
        if not row:
            continue
        disease = row[0].strip()
        if not disease:
            continue
        _record_row(disease, {cell.strip() for cell in row[1:] if cell.strip()})

with open("final_symptoms_to_disease.csv", newline="", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    next(reader)  # header
    for row in reader:
        if not row:
            continue
        disease = row[0].strip()
        if not disease:
            continue
        symptoms_in_row = set()
        for cell in row[1].split(","):
            cell = cell.strip()
            if not cell:
                continue
            words = cell.split(" ")
            if "and" in words or "or" in words:
                current_words = []
                for word in words:
                    if word in ("and", "or"):
                        if current_words:
                            symptoms_in_row.add(" ".join(current_words))
                            current_words = []
                    else:
                        current_words.append(word)
                if current_words:
                    symptoms_in_row.add(" ".join(current_words))
            else:
                symptoms_in_row.add(cell)
        _record_row(disease, symptoms_in_row)

disease_symptom_weight = {}
for disease, symptom_counts in disease_symptom_rows.items():
    total_rows = disease_rows[disease]
    disease_symptom_weight[disease] = {
        symptom: round(count / total_rows * 100) for symptom, count in symptom_counts.items()
    }

# ------------------------------------------------ 5. WEIGHTING_3: combining previous weighting plus the combined scorer and frequncy od disease 
def base(disease, symptom):
    return symptom_weight[symptom] * (disease_symptom_weight[disease][symptom] / 100)

def boost(k):
    return k ** 1.3

def frequency(disease):
    return disease_rows[disease]

def disease_score(symptoms):
    input_set = set(symptoms)
    the_disease_scores = {}
    for disease, symptom_weights in disease_symptom_weight.items():
        matched = input_set & symptom_weights.keys()
        if not matched:
            continue
        the_disease_scores[disease] = (
            sum(base(disease, s) for s in matched) * boost(len(matched)) * frequency(disease)
        )
    if not the_disease_scores:
        return []
    lo, hi = min(the_disease_scores.values()), max(the_disease_scores.values())
    span = hi - lo or 1
    ranked = {d: (v - lo) * 99 / span + 1 for d, v in the_disease_scores.items()}
    return sorted(ranked.items(), key=lambda x: -x[1])


# --------------------------------------- 6. The LLM stuff
DISEASES = [n for n in G if G.out_degree(n) > 0]
SYMPTOMS = [n for n in G if G.in_degree(n) > 0]

IDF = {s: math.log(len(DISEASES) / G.in_degree(s)) + 1.0 for s in SYMPTOMS}
_UNSEEN_IDF = math.log(len(DISEASES)) + 1.0


def idf(symptom):
    return IDF.get(symptom, _UNSEEN_IDF)


_READABLE = {s.replace("_", " ").strip().lower(): s for s in SYMPTOMS}

SYNONYMS = {
    "throwing up": "vomiting", "puking": "vomiting", "being sick": "vomiting",
    "high temperature": "high_fever", "temperature": "high_fever",
    "fever": "high_fever", "hot": "high_fever",
    "no appetite": "loss_of_appetite", "not hungry": "loss_of_appetite",
    "cant sleep": "restlessness", "tired": "fatigue", "exhausted": "fatigue",
    "short of breath": "breathlessness", "cant breathe": "breathlessness",
    "runny nose": "runny_nose", "blocked nose": "congestion",
    "sore throat": "throat_irritation", "yellow eyes": "yellowing_of_eyes",
    "belly ache": "abdominal_pain", "tummy pain": "abdominal_pain",
    "stomach ache": "stomach_pain", "the runs": "diarrhoea",
    "loose stools": "diarrhoea", "cant poo": "constipation",
    "itchy": "itching", "rash": "skin_rash", "dizzy": "dizziness",
    "sweaty": "sweating", "night sweats": "sweating", "shaky": "shivering",
    "weight loss": "weight_loss", "losing weight": "weight_loss",
    "peeing a lot": "polyuria", "burning when i pee": "burning_micturition",
    "joint ache": "joint_pain", "aching muscles": "muscle_pain",
    "chest tightness": "chest_pain", "heartburn": "acidity",
    "blurry vision": "blurred_and_distorted_vision", "anxious": "anxiety",
    "low mood": "depression", "sneezing": "continuous_sneezing",
    "urination": "micturition",
}
_SYN_KEYS = sorted(SYNONYMS, key=len, reverse=True)


def canonicalise(raw_symptoms):
    """Map free-text symptom phrases onto real graph nodes."""
    matched, unknown = [], []
    for phrase in raw_symptoms:
        needle = str(phrase).replace("_", " ").strip().lower()
        needle = re.sub(r"[^a-z ]", "", needle).strip()
        if not needle:
            continue

        if needle in SYNONYMS:
            matched.append(SYNONYMS[needle])
            continue

        buried = [k for k in _SYN_KEYS if k in needle]
        if buried:
            matched.extend(SYNONYMS[k] for k in buried[:1])
            continue

        hit = process.extractOne(needle, list(_READABLE), scorer=fuzz.token_set_ratio, score_cutoff=75)
        if hit:
            matched.append(_READABLE[hit[0]])
        else:
            unknown.append(str(phrase))
    return sorted(set(matched)), unknown


def score_diseases(symptoms, top_n=5):
    """Weighted-Jaccard rank: rewards matches, penalises misses on both sides."""
    user = set(symptoms)
    results = []
    for disease in DISEASES:
        known = set(G.successors(disease))
        hit = user & known
        if not hit:
            continue
        overlap = sum(idf(s) for s in hit)
        union = sum(idf(s) for s in user | known)
        results.append((overlap / union, disease, sorted(hit), sorted(known - user)))
    results.sort(reverse=True)
    return results[:top_n]


def discriminators(candidates, asked_about, k=3):
    """Symptoms that best split the top candidates."""
    names = [c[1] for c in candidates]
    if len(names) < 2:
        return []

    has_symptom = {d: set(G.successors(d)) for d in names}
    pool = set().union(*has_symptom.values()) - set(asked_about)

    scored = []
    for symptom in pool:
        present = [d for d in names if symptom in has_symptom[d]]
        if not present or len(present) == len(names):
            continue
        balance = 1.0 - abs(len(present) / len(names) - 0.5) * 2
        scored.append((balance * idf(symptom), symptom, present))

    scored.sort(reverse=True)
    return scored[:k]


def diagnose_text(raw_symptoms, top_n=5):
    symptoms, unknown = canonicalise(raw_symptoms)
    if not symptoms:
        return f"No known symptoms matched {raw_symptoms}. Ask the user to rephrase."

    candidates = score_diseases(symptoms, top_n)

    lines = [f"Matched symptoms: {', '.join(symptoms)}"]
    if unknown:
        lines.append(f"Not in the graph (ignored): {', '.join(unknown)}")
    lines.append("")
    lines.append("Ranked candidates:")
    for score, disease, hit, missing in candidates:
        lines.append(f"- {disease} (score {score:.3f}) matched {len(hit)}: {', '.join(hit)}")
        if missing:
            lines.append(f"    also usually presents: {', '.join(missing[:4])}")

    splits = discriminators(candidates, symptoms)
    if splits:
        lines.append("")
        lines.append("Best follow-up questions (these split the candidates):")
        for _, symptom, present in splits:
            lines.append(f"- {symptom}? if yes -> {', '.join(present)}")
    return "\n".join(lines)


# ---------------------------------------------------------------- 7. adding the guardrails
_DISEASE_PATTERNS = {}
for _d in DISEASES:
    _flags = 0 if _d.isupper() else re.IGNORECASE
    _DISEASE_PATTERNS[_d] = re.compile(r"\b" + re.escape(_d) + r"\b", _flags)

OFF_GRAPH = [
    "influenza", "flu", "covid", "coronavirus", "meningitis", "sepsis", "anaemia",
    "anemia", "appendicitis", "gastritis", "pancreatitis", "cholera", "measles",
    "mumps", "rubella", "shingles", "lyme disease", "mononucleosis", "glandular fever",
    "strep throat", "tonsillitis", "bronchitis", "sinusitis", "ulcerative colitis",
    "crohn", "ibs", "cancer", "leukaemia", "leukemia", "lupus", "fibromyalgia",
    "food poisoning", "norovirus", "zika", "ebola", "cystitis", "kidney stones",
    "gallstones", "stroke", "angina", "copd", "emphysema", "eczema", "dermatitis",
]
_OFF_GRAPH_PATTERNS = {n: re.compile(r"\b" + re.escape(n) + r"\b", re.IGNORECASE) for n in OFF_GRAPH}


def diseases_mentioned(text):
    """Which of the graph's diseases appear in a piece of text."""
    return {d for d, pat in _DISEASE_PATTERNS.items() if pat.search(text)}


def ungrounded(reply, tool_output):
    """Disease names in the reply that the graph lookup did not return."""
    strays = sorted(diseases_mentioned(reply) - diseases_mentioned(tool_output))
    strays += sorted(n for n, pat in _OFF_GRAPH_PATTERNS.items() if pat.search(reply))
    return strays


DISCLAIMER = (
    "\n\n---\nThis is a lookup over a small teaching dataset, not clinical "
    "evidence. It is not medical advice - please see a doctor."
)

# ---------------------------------------------------------------- 8. agent + tools
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver


@tool
def use_disease_scorer(symptoms: list[str]) -> str:
    """Score diseases by weighted symptom match - rarer, more specific symptoms
    count for more, and matching several symptoms at once gets a boost.
    Pass symptoms as they appear in the graph, e.g. ["itching", "skin rash"].
    Returns candidate diseases ranked highest-scoring first.
    """
    ranked = disease_score(symptoms)
    if not ranked:
        return f"No diseases matched {symptoms}."
    return "\n".join(f"- {disease} (score {score:.1f})" for disease, score in ranked)


@tool
def diagnose(symptoms: list[str]) -> str:
    """Look up probable diseases for a list of patient symptoms.
    Pass symptoms as short plain-English phrases, e.g. ["headache", "throwing up"].
    They are matched onto the knowledge graph automatically.
    Returns candidate diseases ranked by weighted symptom overlap, plus the best
    follow-up questions to ask.
    """
    return diagnose_text(symptoms)


llm = ChatOpenAI(
    base_url="http://localhost:1234/v1",  # LM Studio's local server
    api_key="lm-studio",
    model="local-model",
    temperature=0,
)

SYSTEM_PROMPT = """You are an assistant exploring a disease-symptom knowledge graph.

Rules:
- ALWAYS call the `diagnose` tool before naming any disease. Never answer from memory.
- Only name diseases that appear in the tool's output. Never introduce another one.
- Accumulate symptoms across the conversation: if the user adds one, resend the
  full list to the tool.
- Constrain to reasoning from the graph
- Report the candidates in the tool's order, with their scores.
- The tool supplies follow-up questions. Ask those. Do not invent your own.
"""

agent = create_agent(
    model=llm,
    tools=[diagnose, use_disease_scorer],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=InMemorySaver(),
)

RESET_PHRASES = {"new conversation", "start over", "new patient", "reset", "new chat", "clear chat"}


def grounded_answer(message):
    phrases = [p.strip() for p in message.replace(",", " and ").split(" and ")]
    return diagnose_text(phrases + [message])


def chat(message, thread_id="patient-1", strict=True):
    """Send one message to the agent and get its (grounded) reply back."""
    if message.strip().lower() in RESET_PHRASES:
        agent.checkpointer.delete_thread(thread_id)
        return "Memory cleared — starting a new conversation."

    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    messages = result["messages"]
    called = any(getattr(m, "tool_calls", None) for m in messages)
    tool_output = "\n".join(m.content for m in messages if m.type == "tool")
    reply = messages[-1].content

    if not called:
        # the model never consulted the graph
        reply = (
            "[the model answered without calling the tool - "
            "showing the graph's answer instead]\n\n" + grounded_answer(message)
        )
    else:
        strays = ungrounded(reply, tool_output)
        if strays and strict:
            # it called the tool, then talked past the result
            reply = (
                f"[reply named {', '.join(strays)}, which the lookup did not "
                f"return - showing the raw lookup instead]\n\n" + tool_output
            )
        elif strays:
            reply += f"\n\n[warning: {', '.join(strays)} did not come from the graph]"

    return reply + DISCLAIMER
