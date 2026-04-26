import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Animated, Easing, SafeAreaView, ScrollView } from 'react-native';
import ReactNativeHapticFeedback from 'react-native-haptic-feedback';
import { VictoryChart, VictoryLine, VictoryAxis, VictoryTheme } from 'victory-native';
import Icon from 'react-native-vector-icons/FontAwesome5';

export type AnomalyLabel = 'NORMAL' | 'CAUTION' | 'EMERGENCY';

interface MonitorScreenProps {
  currentStatus: AnomalyLabel;
  currentHR: number; // Heart rate in BPM
  currentRR: number; // Respiratory rate in breaths/min
  lastMeasurementTime: Date;
  onCallEmergency: () => void;
}

const STATUS_CONFIG = {
  NORMAL: {
    label: 'All normal',
    color: '#22c55e',
    haptic: 'notificationSuccess' as const
  },
  CAUTION: {
    label: 'Check baby',
    color: '#f59e0b',
    haptic: 'notificationWarning' as const
  },
  EMERGENCY: {
    label: 'Go to hospital now',
    color: '#ef4444',
    haptic: 'notificationError' as const
  }
};

/**
 * Animated Pulse Icon that beats synchronously with the current physiological rate
 */
const PulseIcon = ({ name, rate, color }: { name: string, rate: number, color: string }) => {
  const scale = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    scale.stopAnimation();
    if (rate <= 0) {
        scale.setValue(1);
        return;
    }
    
    // Pulse duration exactly matches the inter-beat/inter-breath interval
    const duration = (60 / rate) * 1000; 
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(scale, {
          toValue: 1.25,
          duration: duration * 0.15,
          useNativeDriver: true,
          easing: Easing.out(Easing.ease),
        }),
        Animated.timing(scale, {
          toValue: 1.0,
          duration: duration * 0.85,
          useNativeDriver: true,
          easing: Easing.in(Easing.ease),
        }),
      ])
    );
    animation.start();
    
    return () => animation.stop();
  }, [rate, scale]);

  return (
    <Animated.View style={{ transform: [{ scale }] }}>
      <Icon name={name} size={42} color={color} solid />
    </Animated.View>
  );
};

export const MonitorScreen = ({
  currentStatus,
  currentHR,
  currentRR,
  lastMeasurementTime,
  onCallEmergency
}: MonitorScreenProps) => {
  const config = STATUS_CONFIG[currentStatus];
  const prevStatus = useRef<AnomalyLabel>(currentStatus);

  // Buffer 30-second history for charts (assumes parent pushes updates at 1Hz)
  const [historyHR, setHistoryHR] = useState<{x: number, y: number}[]>([]);
  const [historyRR, setHistoryRR] = useState<{x: number, y: number}[]>([]);

  // 1. Haptic feedback strictly on state transitions
  useEffect(() => {
    if (currentStatus !== prevStatus.current) {
      ReactNativeHapticFeedback.trigger(config.haptic, {
        enableVibrateFallback: true,
        ignoreAndroidSystemSettings: false
      });
      prevStatus.current = currentStatus;
    }
  }, [currentStatus, config.haptic]);

  // 2. Rolling Window Updates
  useEffect(() => {
    const now = Date.now();
    setHistoryHR((prev: {x: number, y: number}[]) => {
      const next = [...prev, { x: now, y: currentHR }];
      return next.length > 30 ? next.slice(next.length - 30) : next;
    });
    setHistoryRR((prev: {x: number, y: number}[]) => {
      const next = [...prev, { x: now, y: currentRR }];
      return next.length > 30 ? next.slice(next.length - 30) : next;
    });
  }, [currentHR, currentRR]);

  const renderChart = (
    data: {x: number, y: number}[],
    color: string,
    yMin: number,
    yMax: number,
    refMin: number,
    refMax: number,
    title: string
  ) => (
    <View style={styles.chartWrapper}>
      <Text style={[styles.chartTitle, { color }]}>{title}</Text>
      <View style={styles.chartInner}>
        <VictoryChart
          theme={VictoryTheme.material}
          height={180}
          padding={{ top: 10, bottom: 20, left: 40, right: 10 }}
          domain={{ y: [yMin, yMax] }}
        >
          {/* Upper Normal Boundary */}
          <VictoryLine
            y={() => refMax}
            style={{ data: { stroke: '#9ca3af', strokeWidth: 1, strokeDasharray: '4,4' } }}
          />
          {/* Lower Normal Boundary */}
          <VictoryLine
            y={() => refMin}
            style={{ data: { stroke: '#9ca3af', strokeWidth: 1, strokeDasharray: '4,4' } }}
          />
          
          <VictoryAxis
            dependentAxis
            tickFormat={(t: number) => Math.round(t)}
            style={{
              axis: { stroke: 'transparent' },
              grid: { stroke: '#e5e7eb' },
              tickLabels: { fontSize: 10, fill: '#6b7280' }
            }}
          />
          {/* Hide X-Axis time values for clean ECG scrolling look */}
          <VictoryAxis
            style={{
              axis: { stroke: '#d1d5db' },
              ticks: { stroke: 'transparent' },
              tickLabels: { fill: 'transparent' }
            }}
          />
          
          <VictoryLine
            data={data}
            interpolation="monotoneX"
            style={{
              data: { stroke: color, strokeWidth: 3 }
            }}
          />
        </VictoryChart>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container}>
        
        {/* Timestamp */}
        <Text style={styles.timestamp}>
          Last Update: {lastMeasurementTime.toLocaleTimeString()}
        </Text>

        {/* 1. Large Semantic Status Badge */}
        <View style={[styles.statusBadge, { backgroundColor: config.color }]}>
          <Text style={styles.statusText}>{config.label}</Text>
        </View>

        {/* 2. Animated Pulse Icons & Live Stats */}
        <View style={styles.statsContainer}>
          <View style={styles.statBox}>
            <PulseIcon name="heart" rate={currentHR} color="#ef4444" />
            <Text style={styles.statValue}>{currentHR}</Text>
            <Text style={styles.statLabel}>BPM</Text>
          </View>
          <View style={styles.statBox}>
            <PulseIcon name="lungs" rate={currentRR} color="#3b82f6" />
            <Text style={styles.statValue}>{currentRR}</Text>
            <Text style={styles.statLabel}>Breaths/min</Text>
          </View>
        </View>

        {/* 3. Waveform Charts (30-second window) */}
        <View style={styles.chartsContainer}>
          {/* Neonatal HR baseline references: 100 to 160 */}
          {renderChart(historyHR, '#ef4444', 60, 200, 100, 160, 'Heart Rate (HR)')}
          
          {/* Neonatal RR baseline references: 30 to 60 */}
          {renderChart(historyRR, '#3b82f6', 10, 80, 30, 60, 'Respiratory Rate (RR)')}
        </View>

        {/* 4. Conditional Emergency Button */}
        {currentStatus === 'EMERGENCY' && (
          <TouchableOpacity 
            style={styles.emergencyButton}
            onPress={onCallEmergency}
            activeOpacity={0.8}
          >
            <Icon name="phone-alt" size={20} color="#fff" style={styles.emergencyIcon} />
            <Text style={styles.emergencyText}>Call Emergency</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#f9fafb'
  },
  container: {
    padding: 20,
    alignItems: 'center'
  },
  timestamp: {
    fontSize: 12,
    color: '#6b7280',
    marginBottom: 16,
    fontWeight: '500'
  },
  statusBadge: {
    width: '100%',
    paddingVertical: 20,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusText: {
    color: '#ffffff',
    fontSize: 24,
    fontWeight: '800',
    textTransform: 'uppercase',
    letterSpacing: 1
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    width: '100%',
    marginBottom: 24,
  },
  statBox: {
    alignItems: 'center',
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 16,
    width: '45%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  statValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#1f2937',
    marginTop: 12,
  },
  statLabel: {
    fontSize: 12,
    color: '#6b7280',
    fontWeight: '600',
    textTransform: 'uppercase',
    marginTop: 4,
  },
  chartsContainer: {
    width: '100%',
  },
  chartWrapper: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    paddingTop: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  chartTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginLeft: 16,
    marginBottom: -10, 
  },
  chartInner: {
    alignItems: 'center',
  },
  emergencyButton: {
    backgroundColor: '#ef4444',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    paddingVertical: 18,
    borderRadius: 100,
    marginTop: 10,
    shadowColor: '#ef4444',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 5,
  },
  emergencyIcon: {
    marginRight: 10,
  },
  emergencyText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: 'bold',
    letterSpacing: 0.5,
  }
});
