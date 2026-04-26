import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, Animated, TouchableWithoutFeedback, Easing } from 'react-native';
import { Audio } from 'expo-av';
import Svg, { Path } from 'react-native-svg';

export type AlertLevel = 'NORMAL' | 'CAUTION' | 'EMERGENCY';
export type AnomalyType = 'NONE' | 'APNEA' | 'TACHYPNEA' | 'GENERAL_CAUTION';

export interface AROverlayProps {
  alertLevel: AlertLevel;
  anomalyType: AnomalyType;
  // Absolute pixel coordinates for the detected bounding box coming from Frame Processors
  babyROI: { x: number; y: number; width: number; height: number };
  currentRR: number; 
  onDismiss: () => void;
}

const INSTRUCTIONS = [
  'Check baby is breathing — watch chest for 5 seconds',
  'Open airway — tilt head slightly back',
  'If no chest movement — call emergency services'
];

/**
 * Breathing Rate Animation comparing Current Fast Rate vs Normal Baseline
 */
const TachypneaBars = ({ currentRR }: { currentRR: number }) => {
  const fastScale = useRef(new Animated.Value(1)).current;
  const normalScale = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    // Current Fast Rate
    fastScale.stopAnimation();
    if (currentRR > 0) {
      const fastDuration = (60 / currentRR) * 1000;
      Animated.loop(
        Animated.sequence([
          Animated.timing(fastScale, { toValue: 1.5, duration: fastDuration * 0.2, useNativeDriver: true }),
          Animated.timing(fastScale, { toValue: 1.0, duration: fastDuration * 0.8, useNativeDriver: true })
        ])
      ).start();
    }

    // Normal Baseline Rate (~40)
    normalScale.stopAnimation();
    const normalDuration = (60 / 40) * 1000;
    Animated.loop(
      Animated.sequence([
        Animated.timing(normalScale, { toValue: 1.5, duration: normalDuration * 0.2, useNativeDriver: true }),
        Animated.timing(normalScale, { toValue: 1.0, duration: normalDuration * 0.8, useNativeDriver: true })
      ])
    ).start();
    
    return () => {
      fastScale.stopAnimation();
      normalScale.stopAnimation();
    };
  }, [currentRR, fastScale, normalScale]);

  return (
    <View style={styles.tachypneaContainer}>
      <Text style={styles.tachypneaTitle}>Breathing Rate Alert</Text>
      <View style={styles.barChart}>
        <View style={styles.barCol}>
          <Animated.View style={[styles.bar, styles.fastBar, { transform: [{ scaleY: fastScale }] }]} />
          <Text style={styles.barLabel}>{currentRR}</Text>
        </View>
        <View style={styles.barCol}>
          <Animated.View style={[styles.bar, styles.normalBar, { transform: [{ scaleY: normalScale }] }]} />
          <Text style={styles.barLabel}>40 (Norm)</Text>
        </View>
      </View>
    </View>
  );
};

export const AROverlay = ({
  alertLevel,
  anomalyType,
  babyROI,
  currentRR,
  onDismiss
}: AROverlayProps) => {
  // 1. Audio Alarm for Apnea
  const soundRef = useRef<any>(null);

  useEffect(() => {
    async function playAlarm() {
      if (anomalyType === 'APNEA' && alertLevel === 'EMERGENCY') {
        try {
          const { sound } = await Audio.Sound.createAsync(
            require('./assets/90db_alarm.mp3'),
            { shouldPlay: true, isLooping: true, volume: 1.0 }
          );
          soundRef.current = sound;
        } catch (error) {
          console.warn('Audio play failed (make sure assets/90db_alarm.mp3 exists)', error);
        }
      }
    }
    
    playAlarm();
    
    return () => {
      if (soundRef.current) {
        soundRef.current.stopAsync();
        soundRef.current.unloadAsync();
      }
    };
  }, [anomalyType, alertLevel]);

  // 2. Cycling Instructions
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (alertLevel === 'NORMAL') return;
    const timer = setInterval(() => {
      setStep((s: number) => (s + 1) % INSTRUCTIONS.length);
    }, 4000);
    return () => clearInterval(timer);
  }, [alertLevel]);

  // 3. 3-Second Hold to Dismiss (Accident Prevention)
  const holdProgress = useRef(new Animated.Value(0)).current;
  const handlePressIn = () => {
    Animated.timing(holdProgress, {
      toValue: 1,
      duration: 3000,
      useNativeDriver: false, // Cannot use native driver when animating width%
      easing: Easing.linear
    }).start(({ finished }: { finished: boolean }) => {
      if (finished) {
        onDismiss();
      }
    });
  };

  const handlePressOut = () => {
    holdProgress.stopAnimation();
    holdProgress.setValue(0);
  };

  const buttonWidth = holdProgress.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%']
  });

  // Do not render AR elements if everything is normal
  if (alertLevel === 'NORMAL') {
    return null; 
  }

  // 4. Critical Apnea Full-Screen Block
  if (anomalyType === 'APNEA') {
    return (
      <View style={styles.fullScreenApnea}>
        <View style={styles.apneaContent}>
          <Text style={styles.apneaEmergencyText}>APNEA DETECTED</Text>
          <Text style={styles.apneaActionText}>CALL EMERGENCY NOW</Text>
          <Text style={styles.apneaSubText}>Baby has stopped breathing.</Text>
        </View>
        
        {/* Hold to Dismiss Button */}
        <TouchableWithoutFeedback onPressIn={handlePressIn} onPressOut={handlePressOut}>
          <View style={styles.dismissButton}>
            <Animated.View style={[styles.dismissProgress, { width: buttonWidth }]} />
            <Text style={styles.dismissText}>HOLD 3 SEC TO DISMISS</Text>
          </View>
        </TouchableWithoutFeedback>
      </View>
    );
  }

  // 5. CAUTION/TACHYPNEA AR Overlay
  const borderColor = alertLevel === 'EMERGENCY' ? 'rgba(239, 68, 68, 0.7)' : 'rgba(245, 158, 11, 0.7)'; // Red or Yellow

  return (
    <View style={styles.overlayContainer} pointerEvents="box-none">
      
      {/* AR Border strictly bound to the vision-camera Frame Processor ROI */}
      <View style={[
        styles.roiBorder, 
        {
          left: babyROI.x,
          top: babyROI.y,
          width: babyROI.width,
          height: babyROI.height,
          borderColor: borderColor
        }
      ]}>
        <Text style={[styles.roiLabel, { backgroundColor: borderColor }]}>BABY ROI</Text>
      </View>

      {/* SVG Silhouette demonstrating correct neutral head tilt position */}
      <View style={styles.silhouetteContainer}>
        <Text style={styles.silhouetteTitle}>Neutral Head Tilt</Text>
        <Svg width="80" height="80" viewBox="0 0 100 100">
           {/* Abstract baby head profile tilted back slightly */}
           <Path d="M50 10 C30 10, 15 25, 15 45 C15 65, 30 75, 40 85 C45 90, 50 95, 60 95 C75 95, 85 80, 85 60 C85 45, 75 25, 65 15 Z" fill="#9ca3af" />
           {/* Airway indicator lines */}
           <Path d="M40 85 L35 100 M60 95 L70 100" stroke="#ef4444" strokeWidth="4" />
        </Svg>
      </View>

      {/* Tachypnea Comparative Analysis */}
      {anomalyType === 'TACHYPNEA' && (
        <TachypneaBars currentRR={currentRR} />
      )}

      {/* Step-by-step Cycling Instruction Card */}
      <View style={styles.instructionCard}>
        <Text style={styles.instructionStep}>Step {step + 1} of 3</Text>
        <Text style={styles.instructionText}>{INSTRUCTIONS[step]}</Text>
      </View>

      {/* Fallback dismiss button for Caution/Tachypnea states */}
      <View style={styles.dismissWrapper}>
        <TouchableWithoutFeedback onPressIn={handlePressIn} onPressOut={handlePressOut}>
          <View style={styles.dismissButton}>
            <Animated.View style={[styles.dismissProgress, { width: buttonWidth }]} />
            <Text style={styles.dismissText}>HOLD 3 SEC TO DISMISS</Text>
          </View>
        </TouchableWithoutFeedback>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  overlayContainer: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 999,
  },
  roiBorder: {
    position: 'absolute',
    borderWidth: 4,
    borderStyle: 'dashed',
    borderRadius: 8,
  },
  roiLabel: {
    position: 'absolute',
    top: -24,
    left: -4,
    color: '#fff',
    fontWeight: 'bold',
    paddingHorizontal: 8,
    paddingVertical: 4,
    fontSize: 12,
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
  },
  silhouetteContainer: {
    position: 'absolute',
    top: 60,
    right: 20,
    backgroundColor: 'rgba(255,255,255,0.9)',
    padding: 10,
    borderRadius: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
  },
  silhouetteTitle: {
    fontSize: 10,
    fontWeight: 'bold',
    marginBottom: 4,
    color: '#374151'
  },
  tachypneaContainer: {
    position: 'absolute',
    top: 60,
    left: 20,
    backgroundColor: 'rgba(255,255,255,0.9)',
    padding: 10,
    borderRadius: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
  },
  tachypneaTitle: {
    fontSize: 10,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#ef4444'
  },
  barChart: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    height: 60,
  },
  barCol: {
    alignItems: 'center',
    marginHorizontal: 8,
  },
  bar: {
    width: 16,
    borderRadius: 4,
  },
  fastBar: {
    height: 35,
    backgroundColor: '#ef4444',
  },
  normalBar: {
    height: 25,
    backgroundColor: '#22c55e',
  },
  barLabel: {
    fontSize: 10,
    marginTop: 4,
    fontWeight: '600'
  },
  instructionCard: {
    position: 'absolute',
    bottom: 120,
    alignSelf: 'center',
    width: '90%',
    backgroundColor: 'rgba(0,0,0,0.85)',
    padding: 20,
    borderRadius: 16,
    alignItems: 'center',
  },
  instructionStep: {
    color: '#f59e0b',
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 8,
    textTransform: 'uppercase'
  },
  instructionText: {
    color: '#fff',
    fontSize: 18,
    textAlign: 'center',
    fontWeight: '600'
  },
  dismissWrapper: {
    position: 'absolute',
    bottom: 40,
    alignSelf: 'center',
    width: '90%',
  },
  dismissButton: {
    width: '100%',
    height: 50,
    backgroundColor: '#374151',
    borderRadius: 25,
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  dismissProgress: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    backgroundColor: '#ef4444', // Red fill progress indicating hold
  },
  dismissText: {
    color: '#fff',
    fontWeight: 'bold',
    zIndex: 1,
  },
  fullScreenApnea: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(239, 68, 68, 0.95)',
    zIndex: 1000,
    justifyContent: 'space-between',
    paddingBottom: 40,
    paddingTop: 100,
    paddingHorizontal: 20,
    alignItems: 'center'
  },
  apneaContent: {
    alignItems: 'center'
  },
  apneaEmergencyText: {
    fontSize: 32,
    fontWeight: '900',
    color: '#fff',
    textAlign: 'center',
    marginBottom: 20,
  },
  apneaActionText: {
    fontSize: 48,
    fontWeight: '900',
    color: '#fff',
    textAlign: 'center',
    textTransform: 'uppercase',
    marginBottom: 16,
  },
  apneaSubText: {
    fontSize: 20,
    color: '#fee2e2',
    textAlign: 'center',
  }
});
