/**
 * ==========================================================================
 * SWISS EMERGENCY GRID - CORE JAVASCRIPT ENGINE
 * Geolocation, Audio Web Speech, Live Alarm Chime & Polling
 * ==========================================================================
 */

// 1. Synthetic Audio Alarm Chime (Uses Web Audio API - Works everywhere with zero audio files!)
class EmergencyAudioChime {
  constructor() {
    this.ctx = null;
  }

  initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
  }

  playSirenAlarm() {
    try {
      this.initContext();
      if (!this.ctx) return;

      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();

      osc.type = 'sawtooth';
      // Two-tone European / Swiss emergency siren frequency modulation
      const now = this.ctx.currentTime;
      osc.frequency.setValueAtTime(800, now);
      osc.frequency.linearRampToValueAtTime(1200, now + 0.35);
      osc.frequency.linearRampToValueAtTime(800, now + 0.70);
      osc.frequency.linearRampToValueAtTime(1200, now + 1.05);

      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 1.3);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start(now);
      osc.stop(now + 1.35);
    } catch (e) {
      console.log('Audio chime error:', e);
    }
  }
}

const emergencyChime = new EmergencyAudioChime();

// 2. GPS Location Fetcher
function fetchCurrentGPS(inputElementId, latElementId, lngElementId, statusElementId) {
  const inputEl = document.getElementById(inputElementId);
  const latEl = document.getElementById(latElementId);
  const lngEl = document.getElementById(lngElementId);
  const statusEl = document.getElementById(statusElementId);

  if (!navigator.geolocation) {
    alert("Geolocation is not supported by your current browser.");
    return;
  }

  if (statusEl) {
    statusEl.innerHTML = `<span style="color:#2563EB;">📍 Acquiring GPS satellite fix...</span>`;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      const accuracy = Math.round(position.coords.accuracy);

      if (latEl) latEl.value = lat;
      if (lngEl) lngEl.value = lng;

      // Populate user's location input box directly
      const formattedLoc = `GPS Lat: ${lat.toFixed(5)}, Lng: ${lng.toFixed(5)} (±${accuracy}m)`;
      if (inputEl) inputEl.value = formattedLoc;

      if (statusEl) {
        statusEl.innerHTML = `<span style="color:#059669; font-weight:700;">✓ GPS Coordinates Locked: ${lat.toFixed(4)}, ${lng.toFixed(4)}</span>`;
      }
    },
    (error) => {
      console.warn("GPS lookup error:", error.message);
      // Fallback to municipal default location coordinates
      if (latEl) latEl.value = "40.12118";
      if (lngEl) lngEl.value = "-75.35197";
      if (inputEl && !inputEl.value) inputEl.value = "742 Evergreen Terrace, Sector 4";
      if (statusEl) {
        statusEl.innerHTML = `<span style="color:#D97706;">Using default municipal dispatch sector.</span>`;
      }
    },
    { enableHighAccuracy: true, timeout: 8000, maximumAge: 0 }
  );
}

// 3. Web Speech Recognition (Microphone Speech-to-Text in English, Telugu, Hindi)
let speechRecognizer = null;
let isRecognizing = false;

function initSpeechRecognition(textAreaId, langSelectId, micButtonId, waveformId) {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  const textArea = document.getElementById(textAreaId);
  const langSelect = document.getElementById(langSelectId);
  const micBtn = document.getElementById(micButtonId);
  const waveBox = document.getElementById(waveformId);

  if (!SpeechRec) {
    alert("Speech Recognition is supported in Chrome, Edge, and modern browsers. You can also type text or upload an audio file.");
    return;
  }

  if (isRecognizing && speechRecognizer) {
    speechRecognizer.stop();
    isRecognizing = false;
    if (micBtn) micBtn.innerHTML = `🎙️ Start Live Mic Recording`;
    if (waveBox) waveBox.style.display = 'none';
    return;
  }

  speechRecognizer = new SpeechRec();
  speechRecognizer.continuous = true;
  speechRecognizer.interimResults = true;

  // Language mapping
  let selectedLang = langSelect ? langSelect.value : 'English';
  if (selectedLang === 'Telugu') {
    speechRecognizer.lang = 'te-IN';
  } else if (selectedLang === 'Hindi') {
    speechRecognizer.lang = 'hi-IN';
  } else {
    speechRecognizer.lang = 'en-US';
  }

  speechRecognizer.onstart = function () {
    isRecognizing = true;
    if (micBtn) micBtn.innerHTML = `⏹️ Stop Recording (Listening...)`;
    if (waveBox) waveBox.style.display = 'flex';
  };

  speechRecognizer.onresult = function (event) {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript;
    }
    if (textArea) {
      textArea.value = transcript;
    }
  };

  speechRecognizer.onerror = function (event) {
    console.error("Speech Recognition Error:", event.error);
    isRecognizing = false;
    if (micBtn) micBtn.innerHTML = `🎙️ Start Live Mic Recording`;
    if (waveBox) waveBox.style.display = 'none';
  };

  speechRecognizer.onend = function () {
    isRecognizing = false;
    if (micBtn) micBtn.innerHTML = `🎙️ Start Live Mic Recording`;
    if (waveBox) waveBox.style.display = 'none';
  };

  speechRecognizer.start();
}

// 4. Emergency Preset Injector
function applyEmergencyPreset(presetType) {
  const locInput = document.getElementById('id_location');
  const textInput = document.getElementById('id_call_text');
  const langSelect = document.getElementById('id_language');

  if (!locInput || !textInput) return;

  if (presetType === 'burglary') {
    locInput.value = "1042 Oakridge Ave, Sector 8";
    textInput.value = "Someone broke into my back window right now with a crowbar! I am locked inside the bathroom and terrified, please send police fast!";
    if (langSelect) langSelect.value = "English";
  } else if (presetType === 'accident') {
    locInput.value = "Highway 101 Northbound & Exit 42 Overpass";
    textInput.value = "Severe head-on collision between two cars, smoke is pouring out, driver is bleeding heavily and trapped inside the vehicle, hurry!";
    if (langSelect) langSelect.value = "English";
  } else if (presetType === 'telugu') {
    locInput.value = "Plot 45, Jubilee Hills Road No 10";
    textInput.value = "మా ఇంట్లోకి ఇద్దరు దొంగలు కత్తులతో చొరబడ్డారు, మమ్మల్ని చంపేస్తామని బెదిరిస్తున్నారు, వెంటనే కాపాడండి!";
    if (langSelect) langSelect.value = "Telugu";
  } else if (presetType === 'hindi') {
    locInput.value = "Civil Lines, Near Metro Gate 3";
    textInput.value = "यहाँ बाजार में दो गाड़ियों की बहुत भयानक टक्कर हुई है, लोग गंभीर रूप से घायल हैं और खून बह रहा है, तुरंत पुलिस भेजो!";
    if (langSelect) langSelect.value = "Hindi";
  } else if (presetType === 'routine') {
    locInput.value = "312 Elm Street, Apt 4B";
    textInput.value = "Hello, my neighbor has been playing extremely loud music in the apartment for three hours, just calling to report a noise disturbance.";
    if (langSelect) langSelect.value = "English";
  }
}

// 5. Police Admin Real-time Alert Polling
let lastCriticalId = null;

function startAdminAlertPolling() {
  setInterval(() => {
    fetch('/api/alerts/')
      .then(res => res.json())
      .then(data => {
        const alertBanner = document.getElementById('live-admin-alert-box');
        const alertContent = document.getElementById('live-alert-text');
        
        if (data.has_critical && data.alerts.length > 0) {
          const topAlert = data.alerts[0];
          if (alertBanner && alertContent) {
            alertContent.innerHTML = `
              <strong>[CRITICAL ${topAlert.priority}] ${topAlert.topic}</strong> &mdash; 
              Caller: ${topAlert.caller} (${topAlert.phone}) at <em>${topAlert.location}</em> 
              [Distress: ${topAlert.distress_percent}%]
            `;
            alertBanner.style.display = 'flex';
          }

          // If new critical incident arrived, trigger siren
          if (topAlert.id !== lastCriticalId) {
            lastCriticalId = topAlert.id;
            emergencyChime.playSirenAlarm();
          }
        }
      })
      .catch(err => console.log('Polling alerts check:', err));
  }, 4000);
}
