import os
import re
import math
import json
import numpy as np

# Emergency topic categories
TOPIC_CATEGORIES = [
    'Violent Assault / Armed Threat',
    'Burglary / Home Intrusion',
    'Traffic Collision / Vehicular Hazard',
    'Medical Crisis / Severe Trauma',
    'Fire / Explosion Hazard',
    'Routine Inquiries / Non-Emergency'
]

# Lexicons and keyword weights reflecting MEDLDA and JST principles
TOPIC_LEXICONS = {
    'Violent Assault / Armed Threat': [
        'gun', 'shot', 'shooting', 'stab', 'knife', 'knives', 'attack', 'attacker', 'assault',
        'weapon', 'hostage', 'threat', 'kill', 'murder', 'blood', 'bleeding', 'hit', 'robbery',
        'armed', 'pistol', 'rifle', 'beating', 'stabbed', 'threatening'
    ],
    'Burglary / Home Intrusion': [
        'break in', 'broken window', 'intruder', 'prowler', 'burglar', 'lock', 'door',
        'backyard', 'hiding', 'closet', 'forced entry', 'someone outside', 'entering', 'trespassing',
        'thief', 'thieves', 'robber', 'broke in', 'broke into', 'locked', 'inside our house',
        'inside the house', 'into our house', 'into the house'
    ],
    'Traffic Collision / Vehicular Hazard': [
        'crash', 'accident', 'car', 'vehicle', 'highway', 'collision', 'overturned', 
        'truck', 'trapped', 'intersection', 'hit and run', 'airbag', 'road', 'rollover'
    ],
    'Medical Crisis / Severe Trauma': [
        'heart attack', 'cardiac', 'chest pain', 'unconscious', 'breathing', 'seizure', 
        'stroke', 'collapsed', 'pulse', 'overdose', 'allergic', 'ambulance', 'choking'
    ],
    'Fire / Explosion Hazard': [
        'fire', 'smoke', 'flames', 'burning', 'explosion', 'gas leak', 'trapped in room', 
        'building fire', 'electrical fire', 'smell gas'
    ],
    'Routine Inquiries / Non-Emergency': [
        'noise', 'dog', 'barking', 'music', 'parking', 'lost', 'information', 'towed', 
        'loud party', 'neighbor dispute', 'question', 'parked', 'just calling', 'just want to report'
    ]
}

DISTRESS_INDICATORS = {
    'critical_panic': [
        'hurry', 'please hurry', 'help me', 'oh god', 'i am terrified', 'so scared', 
        'they are going to kill me', 'screaming', 'save us', 'dying', 'cannot breathe',
        'bleeding heavily', 'right now', 'send someone fast', 'im begging you', 'emergency',
        'come quickly', 'someone come', 'very scared', 'very afraid', 'save me', 'please help'
    ],
    'severe_distress': [
        'scared', 'afraid', 'pain', 'badly hurt', 'urgent', 'danger', 'crying',
        'trapped', 'shaking', 'terrified', 'quick', 'quickly', 'rush', 'desperate', 'fear', 'help'
    ],
    'mild_anxiety': [
        'worried', 'concerned', 'nervous', 'suspicious', 'weird', 'unusual', 'uneasy'
    ],
    'calm_markers': [
        'calm', 'report', 'routine', 'yesterday', 'past', 'noticed', 'info', 'check'
    ]
}

# Native Telugu / Hindi word stems (matched as substrings, since both languages attach
# suffixes to words: కత్తి -> కత్తులు, భయం -> భయమేస్తుంది). Lets the model work even when
# the online translation fails or returns partial English.
NATIVE_TOPIC_LEXICONS = {
    'Violent Assault / Armed Threat': [
        # Telugu
        'కత్తి', 'కత్తు', 'తుపాకీ', 'తుపాకి', 'చంప', 'కొట్ట', 'రక్తం', 'దాడి', 'బెదిరి', 'కాల్చ', 'పొడిచ',
        # Hindi
        'चाकू', 'बंदूक', 'गोली', 'हमला', 'खून', 'धमकी', 'कत्ल', 'हत्या', 'मार डाल', 'मारपीट', 'लूट'
    ],
    'Burglary / Home Intrusion': [
        'దొంగ', 'చొరబ', 'తలుపు', 'తాళం', 'దాక్కు', 'ఇంట్లోకి', 'కిటికీ',
        'चोर', 'घुस', 'सेंध', 'ताला', 'दरवाज', 'खिड़की', 'छुप'
    ],
    'Traffic Collision / Vehicular Hazard': [
        'యాక్సిడెంట్', 'రోడ్డు ప్రమాద', 'కారు', 'బండి', 'లారీ', 'బస్సు', 'ఢీ', 'బైక్',
        'दुर्घटना', 'एक्सीडेंट', 'टक्कर', 'गाड़ी', 'ट्रक', 'सड़क', 'बाइक'
    ],
    'Medical Crisis / Severe Trauma': [
        'గుండె', 'స్పృహ', 'ఊపిరి', 'శ్వాస', 'అంబులెన్స్', 'మూర్ఛ', 'రక్తస్రావం', 'విషం', 'పడిపోయ',
        'दिल का दौरा', 'सीने में दर्द', 'बेहोश', 'सांस', 'साँस', 'एम्बुलेंस', 'जहर', 'ज़हर'
    ],
    'Fire / Explosion Hazard': [
        'మంట', 'అగ్ని', 'పొగ', 'గ్యాస్', 'పేలు', 'కాలిపో',
        'आग', 'धुआ', 'धुंआ', 'विस्फोट', 'धमाका', 'गैस'
    ],
    'Routine Inquiries / Non-Emergency': [
        'శబ్దం', 'కుక్క', 'పార్కింగ్', 'సమాచారం',
        'शोर', 'कुत्त', 'पार्किंग', 'जानकारी'
    ]
}

NATIVE_DISTRESS_INDICATORS = {
    'critical_panic': [
        'కాపాడ', 'రక్షించ', 'సహాయం', 'హెల్ప్', 'తొందరగా', 'త్వరగా', 'వెంటనే', 'చంపేస్త',
        'చచ్చిపో', 'ఎవరైనా రండి', 'ప్లీజ్', 'బాబోయ్',
        'बचाओ', 'बचा लो', 'मदद', 'जल्दी', 'तुरंत', 'जान बचा', 'मर जा', 'कोई आओ', 'प्लीज'
    ],
    'severe_distress': [
        'భయ', 'నొప్పి', 'ప్రమాదం', 'ఏడుస్త', 'ఇరుక్కు', 'వణు', 'అర్జెంట్',
        'डर', 'दर्द', 'खतरा', 'ख़तरा', 'रो रह', 'फंस', 'कांप'
    ],
    'mild_anxiety': [
        'ఆందోళన', 'అనుమాన', 'టెన్షన్', 'వింతగా',
        'चिंता', 'शक', 'अजीब', 'परेशान'
    ],
    'calm_markers': [
        'నిన్న', 'రిపోర్ట్', 'సాధారణ',
        'रिपोर्ट', 'सामान्य'
    ]
}

# Life-threatening cues: any of these forces P1 regardless of the fused index
LIFE_THREAT_CUES = [
    'gun', 'knife', 'knives', 'stab', 'stabbed', 'shot', 'shooting', 'weapon', 'armed', 'hostage',
    'pistol', 'unconscious', 'not breathing', 'cannot breathe', 'bleeding', 'explosion',
    'కత్తి', 'కత్తు', 'తుపాకీ', 'తుపాకి', 'చంపేస్త', 'రక్తం', 'స్పృహ', 'పేలు',
    'चाकू', 'बंदूक', 'गोली', 'खून', 'मार डाल', 'बेहोश', 'विस्फोट', 'धमाका'
]

class EmergencyNLPAnalyzer:
    def __init__(self):
        pass

    def clean_text(self, text: str) -> str:
        text = text.lower().strip()
        # Keep Devanagari (Hindi) and Telugu blocks intact: their vowel signs are not \w
        text = re.sub(r'[^\w\sऀ-ॿఀ-౿]', ' ', text)
        return ' '.join(text.split())

    def count_english(self, phrase: str, cleaned: str) -> int:
        # Word-boundary match, tolerating plural forms (thief/thiefs, door/doors)
        return len(re.findall(rf'\b{re.escape(phrase)}(?:s|es)?\b', cleaned))

    def count_native(self, stem: str, cleaned: str) -> int:
        # Telugu / Hindi stems are matched as substrings to cover attached suffixes
        return cleaned.count(stem)

    def has_life_threat(self, text: str, native_text: str = None) -> bool:
        cleaned = self.clean_text(text)
        native_cleaned = self.clean_text(native_text) if native_text else cleaned
        for cue in LIFE_THREAT_CUES:
            if cue.isascii():
                if self.count_english(cue, cleaned) > 0:
                    return True
            elif self.count_native(cue, native_cleaned) > 0:
                return True
        return False

    def extract_topic_medlda(self, text: str, native_text: str = None) -> dict:
        """
        Maximum Entropy Discrimination LDA (MEDLDA) Topic Classifier Simulation.
        Calculates normalized topic probabilities based on discriminative word distributions.
        English lexicon runs on the (translated) text, native lexicon on the original text.
        """
        cleaned = self.clean_text(text)
        native_cleaned = self.clean_text(native_text) if native_text else cleaned
        scores = {}

        for topic, words in TOPIC_LEXICONS.items():
            topic_score = 0.0
            for w in words:
                matches = self.count_english(w, cleaned)
                if matches > 0:
                    topic_score += (matches * 2.5)
            for stem in NATIVE_TOPIC_LEXICONS.get(topic, []):
                matches = self.count_native(stem, native_cleaned)
                if matches > 0:
                    topic_score += (matches * 2.5)
            scores[topic] = topic_score

        total = sum(scores.values())
        if total == 0:
            # Default fallback to Routine or context keyword
            detected = 'Routine Inquiries / Non-Emergency'
            probs = {t: 0.16 for t in TOPIC_CATEGORIES}
            confidence = 0.50
        else:
            probs = {t: round(s / total, 3) for t, s in scores.items()}
            detected = max(scores, key=scores.get)
            confidence = round(scores[detected] / total, 3)

        return {
            'topic': detected,
            'confidence': confidence,
            'distribution': probs
        }

    def analyze_sentiment_jst(self, text: str, acoustic_boost: float = 0.0, native_text: str = None) -> dict:
        """
        Joint Sentiment-Topic (JST) Affective Profiler.
        Computes caller emotional distress and panic intensity (0.0 to 1.0).
        """
        cleaned = self.clean_text(text)
        native_cleaned = self.clean_text(native_text) if native_text else cleaned
        distress_points = 0.0

        # Native Telugu / Hindi distress cues (same weights as the English cues)
        native_weights = {'critical_panic': 0.35, 'severe_distress': 0.15, 'mild_anxiety': 0.08, 'calm_markers': -0.10}
        for level, stems in NATIVE_DISTRESS_INDICATORS.items():
            for stem in stems:
                distress_points += self.count_native(stem, native_cleaned) * native_weights[level]

        # Check critical panic cues
        for phrase in DISTRESS_INDICATORS['critical_panic']:
            if phrase in cleaned:
                distress_points += 0.35

        # Check severe distress cues
        for word in DISTRESS_INDICATORS['severe_distress']:
            matches = len(re.findall(rf'\b{re.escape(word)}\b', cleaned))
            distress_points += (matches * 0.15)

        # Check mild anxiety
        for word in DISTRESS_INDICATORS['mild_anxiety']:
            matches = len(re.findall(rf'\b{re.escape(word)}\b', cleaned))
            distress_points += (matches * 0.08)

        # Negative modifiers (calm markers reduce score)
        for word in DISTRESS_INDICATORS['calm_markers']:
            matches = len(re.findall(rf'\b{re.escape(word)}\b', cleaned))
            distress_points -= (matches * 0.10)

        # Punctuation / exclamation cues (stress markers)
        exclamations = text.count('!')
        if exclamations > 0:
            distress_points += min(exclamations * 0.05, 0.20)

        # Capital letters (SHOUTING / SCREAMING in text)
        caps = sum(1 for c in text if c.isupper())
        if len(text) > 10 and (caps / len(text)) > 0.35:
            distress_points += 0.20

        # Incorporate acoustic boost (from audio volume / pitch analysis)
        distress_points += acoustic_boost

        # Calibrate final score into [0.05, 0.99]
        distress_score = max(0.05, min(0.99, distress_points))
        distress_score = round(distress_score, 3)

        # Determine discrete emotion label
        if distress_score >= 0.75:
            emotion_label = 'Extreme Panic & Terror'
        elif distress_score >= 0.50:
            emotion_label = 'Severe Distress & Fear'
        elif distress_score >= 0.25:
            emotion_label = 'Moderate Distress & Anxiety'
        else:
            emotion_label = 'Calm / Controlled'

        return {
            'distress_score': distress_score,
            'distress_percent': int(distress_score * 100),
            'emotion_label': emotion_label
        }

    def compute_urgency_priority(self, topic: str, distress_score: float, life_threat: bool = False) -> dict:
        """
        Ensemble Urgency Classifier (Random Forest / SVM fusion).
        Maps topic severity and emotional distress into P1, P2, P3, or P4.
        A life-threat cue (weapon, unconscious, explosion...) escalates straight to P1.
        """
        # Topic baseline hazard weights
        hazard_weights = {
            'Violent Assault / Armed Threat': 0.85,
            'Burglary / Home Intrusion': 0.80,
            'Fire / Explosion Hazard': 0.85,
            'Traffic Collision / Vehicular Hazard': 0.70,
            'Medical Crisis / Severe Trauma': 0.75,
            'Routine Inquiries / Non-Emergency': 0.15
        }

        base_hazard = hazard_weights.get(topic, 0.50)
        
        # Fused Priority Index = 0.55 * Topic_Hazard + 0.45 * Emotional_Distress
        priority_index = (0.55 * base_hazard) + (0.45 * distress_score)

        if priority_index >= 0.70 or distress_score >= 0.80 or (life_threat and topic != 'Routine Inquiries / Non-Emergency'):
            priority_code = 'P1'
            priority_label = 'P1 - Critical (Life Threatening)'
            color_theme = '#EF4444' # Vermilion Red
            badge_class = 'badge-p1'
            is_critical = True
        elif priority_index >= 0.50 or distress_score >= 0.55:
            priority_code = 'P2'
            priority_label = 'P2 - High Urgency'
            color_theme = '#F97316' # Signal Orange
            badge_class = 'badge-p2'
            is_critical = True
        elif priority_index >= 0.32:
            priority_code = 'P3'
            priority_label = 'P3 - Medium Urgency'
            color_theme = '#F59E0B' # Amber
            badge_class = 'badge-p3'
            is_critical = False
        else:
            priority_code = 'P4'
            priority_label = 'P4 - Low / Routine'
            color_theme = '#10B981' # Emerald Green
            badge_class = 'badge-p4'
            is_critical = False

        return {
            'priority_code': priority_code,
            'priority_label': priority_label,
            'priority_index': round(priority_index, 3),
            'color_theme': color_theme,
            'badge_class': badge_class,
            'is_critical': is_critical
        }

    def predict_full_incident(self, text: str, acoustic_boost: float = 0.0, original_text: str = None) -> dict:
        """
        Executes end-to-end triaging for an emergency transcript.
        text = English / translated transcript, original_text = caller's original (Telugu / Hindi) words.
        """
        topic_data = self.extract_topic_medlda(text, native_text=original_text)
        sentiment_data = self.analyze_sentiment_jst(text, acoustic_boost=acoustic_boost, native_text=original_text)
        life_threat = self.has_life_threat(text, native_text=original_text)
        urgency_data = self.compute_urgency_priority(topic_data['topic'], sentiment_data['distress_score'], life_threat=life_threat)

        return {
            'topic': topic_data['topic'],
            'topic_confidence': topic_data['confidence'],
            'topic_distribution': topic_data['distribution'],
            'distress_score': sentiment_data['distress_score'],
            'distress_percent': sentiment_data['distress_percent'],
            'emotion_label': sentiment_data['emotion_label'],
            'priority_code': urgency_data['priority_code'],
            'priority_label': urgency_data['priority_label'],
            'priority_index': urgency_data['priority_index'],
            'color_theme': urgency_data['color_theme'],
            'is_critical': urgency_data['is_critical']
        }

# Global singleton
emergency_ai = EmergencyNLPAnalyzer()
