import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import * as Speech from 'expo-speech';
import AsyncStorage from '@react-native-async-storage/async-storage';

export type AlertLevel = 'NORMAL' | 'CAUTION' | 'EMERGENCY';
export type LanguageCode = 'en' | 'hi' | 'ta' | 'es';

interface VoiceGuideProps {
  alertLevel: AlertLevel;
  currentInstructionStep?: string; 
  isSystemSilent?: boolean; // Mock prop representing system ringer/audio state
}

const TRANSLATIONS = {
  en: {
    caution: "Baby's breathing is slightly fast. Watch closely.",
    emergency: "Warning. Baby may need help. Check breathing and go to hospital.",
    muted: "Sound is muted — check screen for instructions",
    name: "English"
  },
  hi: {
    caution: "Bache ki saans thodi tez hai. Dhyan se dekhein.",
    emergency: "Chetawani. Bache ko madad ki zarurat ho sakti hai. Saans check karein aur aspatal jayein.",
    muted: "Awaaz mute hai — nirdeshon ke liye screen dekhein",
    name: "Hindi"
  },
  ta: {
    caution: "Kuzhandhaiyin moochu konjam vegamaaga ulladhu. Kanippaaga paarkavum.",
    emergency: "Echarikkai. Kuzhandhaikku udhavi thevaippadalaam. Moochu parisoathithu maruthuvamanaikku sella vum.",
    muted: "Oli nirthappattulladhu — thiraikku nirdeshangalai paarkavum",
    name: "Tamil"
  },
  es: {
    caution: "La respiración del bebé es un poco rápida. Observe de cerca.",
    emergency: "Advertencia. El bebé puede necesitar ayuda. Controle la respiración y vaya al hospital.",
    muted: "El sonido está silenciado: revise la pantalla para obtener instrucciones",
    name: "Español"
  }
};

const SPEECH_LANG_CODES = {
  en: 'en-US',
  hi: 'hi-IN',
  ta: 'ta-IN',
  es: 'es-ES'
};

export const VoiceGuide = ({ 
  alertLevel, 
  currentInstructionStep,
  isSystemSilent = false
}: VoiceGuideProps) => {
  const [lang, setLang] = useState<LanguageCode>('en');
  const [showMutedBanner, setShowMutedBanner] = useState(false);
  const emergencyIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 1. Load language preference on mount
  useEffect(() => {
    AsyncStorage.getItem('@voice_lang').then((storedLang: string | null) => {
      if (storedLang && Object.keys(TRANSLATIONS).includes(storedLang)) {
        setLang(storedLang as LanguageCode);
      }
    });
  }, []);

  const changeLanguage = async (newLang: LanguageCode) => {
    setLang(newLang);
    await AsyncStorage.setItem('@voice_lang', newLang);
    Speech.stop(); // Stop current language mid-sentence to avoid overlap
  };

  const handleSpeak = (text: string, forceStopFirst = false) => {
    if (isSystemSilent) {
      setShowMutedBanner(true);
      return;
    }
    
    // Clear banner if we transitioned out of silent mode
    setShowMutedBanner(false);
    
    if (forceStopFirst) {
      Speech.stop();
    }
    
    Speech.speak(text, { language: SPEECH_LANG_CODES[lang] });
  };

  // 2. Alert State Logic
  useEffect(() => {
    // Clear any existing repeating emergency intervals
    if (emergencyIntervalRef.current) {
      clearInterval(emergencyIntervalRef.current);
      emergencyIntervalRef.current = null;
    }

    if (alertLevel === 'NORMAL') {
      Speech.stop();
      setShowMutedBanner(false);
    } 
    else if (alertLevel === 'CAUTION') {
      handleSpeak(TRANSLATIONS[lang].caution, true);
    } 
    else if (alertLevel === 'EMERGENCY') {
      // Speak immediately, then forcefully repeat every 15 seconds
      const triggerEmergencySpeech = () => handleSpeak(TRANSLATIONS[lang].emergency, true);
      triggerEmergencySpeech();
      emergencyIntervalRef.current = setInterval(triggerEmergencySpeech, 15000);
    }

    return () => {
      if (emergencyIntervalRef.current) clearInterval(emergencyIntervalRef.current);
    };
  }, [alertLevel, lang, isSystemSilent]);

  // 3. AR Instruction Step Logic
  useEffect(() => {
    if (currentInstructionStep && alertLevel !== 'NORMAL') {
      // Don't force stop here; let it naturally queue alongside the emergency warning
      handleSpeak(currentInstructionStep, false);
    }
  }, [currentInstructionStep, lang, isSystemSilent, alertLevel]);

  return (
    <View style={styles.container} pointerEvents="box-none">
      {/* Fallback Muted Banner */}
      {showMutedBanner && alertLevel !== 'NORMAL' && (
        <View style={styles.mutedBanner}>
          <Text style={styles.mutedText}>{TRANSLATIONS[lang].muted}</Text>
        </View>
      )}

      {/* Localized Language Selector Overlay */}
      <View style={styles.langSelector}>
        {(Object.keys(TRANSLATIONS) as LanguageCode[]).map((l) => (
          <TouchableOpacity 
            key={l} 
            style={[styles.langBtn, lang === l && styles.langBtnActive]}
            onPress={() => changeLanguage(l)}
          >
            <Text style={[styles.langText, lang === l && styles.langTextActive]}>
              {TRANSLATIONS[l].name}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 1000,
    justifyContent: 'flex-start',
    paddingTop: 80, // Sits comfortably below the top safe area but above AR components
  },
  mutedBanner: {
    backgroundColor: 'rgba(239, 68, 68, 0.95)',
    marginHorizontal: 20,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
  },
  mutedText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
    textAlign: 'center'
  },
  langSelector: {
    flexDirection: 'row',
    justifyContent: 'center',
    flexWrap: 'wrap',
    paddingHorizontal: 20,
  },
  langBtn: {
    backgroundColor: 'rgba(255,255,255,0.85)',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 20,
    marginHorizontal: 4,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#d1d5db'
  },
  langBtnActive: {
    backgroundColor: '#3b82f6',
    borderColor: '#3b82f6'
  },
  langText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#4b5563'
  },
  langTextActive: {
    color: '#ffffff'
  }
});
