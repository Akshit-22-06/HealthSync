# ============================================
# HEALTHSYNC SYMPTOM CHECKER ENGINE
# FULL VERSION — FIXED FLOW (OPTION A)
# ============================================


# -------------------------------
# GLOBAL QUESTION BANK
# (Merged from your disease files)
# -------------------------------

QUESTIONS = [
    {"id": "fever", "text": "Do you have a fever?", "type": "yes_no"},
    {"id": "conjunctivitis", "text": "Do you have red watery eyes?", "type": "yes_no"},
    {"id": "koplik_spots", "text": "Do you see white spots inside the mouth?", "type": "yes_no"},
    {"id": "rash_face_spread", "text": "Is there a rash spreading from face downwards?", "type": "yes_no"},
    {"id": "pink_rash", "text": "Do you have a pink rash?", "type": "yes_no"},
    {"id": "joint_pain", "text": "Do you have joint pain?", "type": "yes_no"},
    {"id": "itchy_rash", "text": "Is the rash itchy?", "type": "yes_no"},
    {"id": "fluid_blisters", "text": "Does the rash look like fluid-filled blisters?", "type": "yes_no"},
    {"id": "burning_pain", "text": "Is the rash painful or burning?", "type": "yes_no"},
    {"id": "unilateral_rash", "text": "Is rash only on one side of body?", "type": "yes_no"},
    {"id": "jaw_swelling", "text": "Is there swelling near jaw or ear?", "type": "yes_no"},
    {"id": "high_fever", "text": "Is the fever high grade?", "type": "yes_no"},
    {"id": "altered_mental_state", "text": "Is there confusion or drowsiness?", "type": "yes_no"},
    {"id": "seizures", "text": "Have there been seizures?", "type": "yes_no"},
    {"id": "eye_pain", "text": "Do you have pain behind the eyes?", "type": "yes_no"},
    {"id": "severe_body_pain", "text": "Is the body pain severe?", "type": "yes_no"},
    {"id": "bleeding_signs", "text": "Is there any bleeding?", "type": "yes_no"},
    {"id": "watery_diarrhea", "text": "Is there watery diarrhea?", "type": "yes_no"},
    {"id": "vomiting", "text": "Is there vomiting?", "type": "yes_no"},
    {"id": "dehydration_signs", "text": "Are there signs of dehydration?", "type": "yes_no"},
    {"id": "sudden_limb_weakness", "text": "Is there sudden weakness in a limb?", "type": "yes_no"},
    {"id": "neck_stiffness", "text": "Is there neck stiffness?", "type": "yes_no"},
    {"id": "swallowing_breathing_difficulty", "text": "Difficulty breathing or swallowing?", "type": "yes_no"},
    {"id": "muscle_aches", "text": "Do you have severe muscle aches?", "type": "yes_no"},
    {"id": "cough", "text": "Do you have cough?", "type": "yes_no"},
    {"id": "weight_loss", "text": "Is there persistent weight loss?", "type": "yes_no"},
    {"id": "chronic_diarrhea", "text": "Is diarrhea lasting >30 days?", "type": "yes_no"},
    {"id": "oral_thrush", "text": "White patches in mouth?", "type": "yes_no"},
]


# --------------------------------
# DISEASE RULE ENGINE
# (Based EXACTLY on your document)
# --------------------------------

DISEASES = [

    {
        "id": "measles",
        "display": "Measles (Rubeola)",
        "min_score": 5,
        "message": "Measles is highly contagious. Isolate immediately and consult doctor.",
        "score_map": {
            "rash_face_spread": 3,
            "koplik_spots": 3,
            "fever": 2,
            "conjunctivitis": 2,
        },
    },

    {
        "id": "rubella",
        "display": "Rubella",
        "min_score": 5,
        "message": "Rubella is mild but dangerous in pregnancy.",
        "score_map": {
            "pink_rash": 2,
            "joint_pain": 1,
        },
    },

    {
        "id": "chickenpox",
        "display": "Chickenpox",
        "min_score": 5,
        "message": "Chickenpox is contagious until lesions crust.",
        "score_map": {
            "fluid_blisters": 3,
            "itchy_rash": 2,
            "fever": 2,
        },
    },

    {
        "id": "shingles",
        "display": "Herpes Zoster (Shingles)",
        "min_score": 6,
        "message": "Shingles is varicella reactivation.",
        "score_map": {
            "unilateral_rash": 3,
            "burning_pain": 3,
        },
    },

    {
        "id": "dengue",
        "display": "Dengue Fever",
        "min_score": 6,
        "message": "Monitor bleeding and hydration carefully.",
        "score_map": {
            "bleeding_signs": 3,
            "severe_body_pain": 2,
            "eye_pain": 2,
        },
    },

    {
        "id": "influenza",
        "display": "Influenza",
        "min_score": 6,
        "message": "Rest and monitor fever. Antivirals early help.",
        "score_map": {
            "high_fever": 3,
            "muscle_aches": 2,
            "cough": 2,
        },
    },

]


# --------------------------------
# QUESTION GETTER
# --------------------------------

def get_question_by_index(index):
    if index < len(QUESTIONS):
        return QUESTIONS[index]
    return None


# --------------------------------
# MAIN ENGINE FUNCTION
# --------------------------------

def run_engine(user_answers):

    results = []

    for disease in DISEASES:

        score = 0

        for q_id, weight in disease["score_map"].items():

            if user_answers.get(q_id) == "yes":
                score += weight

        if score >= disease["min_score"]:
            results.append({
                "name": disease["display"],
                "message": disease["message"],
                "score": score
            })

    return results
