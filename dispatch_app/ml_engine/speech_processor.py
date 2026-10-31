import os
import wave
import json
import urllib.request
import urllib.parse
import numpy as np

try:
    import soundfile as sf
except ImportError:
    sf = None

class SpeechAndAudioProcessor:
    def __init__(self):
        pass

    def extract_acoustic_features(self, audio_path: str) -> dict:
        """
        Analyzes audio waveform for acoustic stress markers (RMS volume, energy, pitch variance).
        Returns acoustic distress boost (0.0 to 0.25).
        """
        if not os.path.exists(audio_path):
            return {'rms_energy': 0.0, 'acoustic_boost': 0.0, 'duration_sec': 0.0}

        try:
            # Use soundfile if available
            if sf:
                data, samplerate = sf.read(audio_path)
                if len(data.shape) > 1:
                    data = data[:, 0]  # mono
                duration = len(data) / float(samplerate)
                rms = float(np.sqrt(np.mean(data**2)))
                peak = float(np.max(np.abs(data)))
            else:
                with wave.open(audio_path, 'rb') as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    duration = frames / float(rate)
                    raw_data = wf.readframes(frames)
                    audio_array = np.frombuffer(raw_data, dtype=np.int16)
                    audio_norm = audio_array / 32768.0
                    rms = float(np.sqrt(np.mean(audio_norm**2)))
                    peak = float(np.max(np.abs(audio_norm)))

            # High RMS energy or high peak indicates shouting, screaming, or sirens
            if rms > 0.25 or peak > 0.85:
                boost = 0.25  # Extreme acoustic volume / shouting
                stress_cue = "High vocal intensity / potential shouting detected"
            elif rms > 0.15 or peak > 0.65:
                boost = 0.15  # Elevated stress
                stress_cue = "Elevated acoustic energy / rapid speech"
            elif rms > 0.08:
                boost = 0.05
                stress_cue = "Normal vocal volume"
            else:
                boost = 0.00
                stress_cue = "Low volume / quiet speech"

            return {
                'rms_energy': round(rms, 4),
                'peak_amplitude': round(peak, 4),
                'duration_sec': round(duration, 2),
                'acoustic_boost': boost,
                'stress_cue': stress_cue
            }
        except Exception as e:
            print(f"Error reading audio {audio_path}: {e}")
            return {'rms_energy': 0.05, 'acoustic_boost': 0.0, 'duration_sec': 0.0, 'stress_cue': 'Standard audio'}

    def detect_language(self, text: str, selected_lang: str = 'English') -> str:
        """
        Detects Telugu / Hindi from the Unicode script of the text, so a native transcript
        is still translated even if the language dropdown was left on English.
        """
        if not text:
            return selected_lang
        if any('ఀ' <= ch <= '౿' for ch in text):
            return 'Telugu'
        if any('ऀ' <= ch <= 'ॿ' for ch in text):
            return 'Hindi'
        return selected_lang

    def translate_to_english(self, text: str, source_lang: str) -> str:
        """
        Translates Hindi or Telugu text to English using public Google Translate endpoint.
        """
        if not text or source_lang == 'en' or source_lang.lower() == 'english':
            return text

        lang_code = 'te' if 'telugu' in source_lang.lower() or source_lang == 'te' else (
            'hi' if 'hindi' in source_lang.lower() or source_lang == 'hi' else 'auto'
        )

        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={lang_code}&tl=en&dt=t&q={urllib.parse.quote(text)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode())
                translated_parts = [part[0] for part in result[0] if part[0]]
                return " ".join(translated_parts)
        except Exception as e:
            print(f"Translation API error: {e}")
            # Offline dictionary fallback for common Telugu/Hindi emergency keywords
            keyword_replacements = {
                'దొంగ': 'thief', 'కత్తి': 'knife', 'కాపాడండి': 'help / save me',
                'రక్తం': 'blood', 'యాక్సిడెంట్': 'accident', 'మంటలు': 'fire',
                'చంపేస్తా': 'kill', 'భయం': 'fear / scared', 'ఇల్లు': 'house',
                'चोर': 'thief', 'चाकू': 'knife', 'बचाओ': 'help / save me',
                'खून': 'blood', 'दुर्घटना': 'accident', 'आग': 'fire',
                'मार': 'kill / beat', 'डर': 'fear / scared', 'घर': 'house'
            }
            res = text
            for k, v in keyword_replacements.items():
                res = res.replace(k, v)
            return res

# Global singleton
audio_processor = SpeechAndAudioProcessor()
