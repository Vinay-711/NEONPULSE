import AsyncStorage from '@react-native-async-storage/async-storage';
import { doc, setDoc, getFirestore } from 'firebase/firestore';
import NetInfo from '@react-native-community/netinfo';

const BUFFER_KEY = '@vital_events_buffer';
const MAX_BUFFER_SIZE = 500;

export interface VitalEvent {
  timestamp: string; // ISO-8601 string mapping to Document ID
  hr_bpm: number;
  rr_bpm: number;
  alert_state: 'NORMAL' | 'CAUTION' | 'EMERGENCY';
  hr_confidence: number;
  rr_confidence: number;
  device_id: string;
  baby_age_days: number;
}

/**
 * Parent-side background relay.
 * Manually manages a localized offline-first buffer limiting strictly to 500 events
 * before attempting to sync to Firestore every 30 seconds upon network recovery.
 */
export class VitalDataRelay {
  private sessionId: string;
  private db = getFirestore();
  private isOnline = false;
  private syncInProgress = false;
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
    
    // Bind robust connectivity listener
    NetInfo.addEventListener((state: any) => {
      this.isOnline = !!state.isConnected && !!state.isInternetReachable;
      if (this.isOnline) {
        this.syncBuffer();
      }
    });
  }

  /**
   * Intended to be called locally by the anomaly pipeline as frequently as needed.
   */
  public async logEvent(event: VitalEvent) {
    // We strictly buffer it first to uphold the AsyncStorage offline-first constraint
    await this.bufferEvent(event);
  }

  /**
   * Initializes the 30-second batch upload loop.
   */
  public startRelayService() {
    this.timer = setInterval(() => {
      if (this.isOnline) {
        this.syncBuffer();
      }
    }, 30000);
  }

  public stopRelayService() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  private async uploadEvent(event: VitalEvent) {
    const eventRef = doc(this.db, `sessions/${this.sessionId}/events/${event.timestamp}`);
    // Will throw if Firebase rules reject (e.g. unauthenticated)
    await setDoc(eventRef, event);
  }

  private async bufferEvent(event: VitalEvent) {
    try {
      const stored = await AsyncStorage.getItem(BUFFER_KEY);
      let buffer: VitalEvent[] = stored ? JSON.parse(stored) : [];
      
      buffer.push(event);
      
      // Enforce the 500 event cap natively in AsyncStorage to prevent heap exhaustion
      if (buffer.length > MAX_BUFFER_SIZE) {
        buffer = buffer.slice(buffer.length - MAX_BUFFER_SIZE);
      }
      
      await AsyncStorage.setItem(BUFFER_KEY, JSON.stringify(buffer));
    } catch (e) {
      console.error('Failed to buffer vital event', e);
    }
  }

  /**
   * Drains the AsyncStorage buffer synchronously and pushes events to Firestore.
   */
  public async syncBuffer() {
    if (this.syncInProgress) return;
    
    try {
      this.syncInProgress = true;
      const stored = await AsyncStorage.getItem(BUFFER_KEY);
      if (!stored) return;
      
      const buffer: VitalEvent[] = JSON.parse(stored);
      if (buffer.length === 0) return;
      
      const remainingBuffer: VitalEvent[] = [];
      
      // We process sequentially. In a high-throughput env, a Promise.allSettled batch write is better,
      // but sequential prevents network throttling.
      for (const event of buffer) {
        try {
          await this.uploadEvent(event);
        } catch (e) {
          // If a specific upload fails (network drop, timeout), preserve it in the buffer
          remainingBuffer.push(event);
        }
      }
      
      // Overwrite storage with whatever didn't make it up to the cloud
      await AsyncStorage.setItem(BUFFER_KEY, JSON.stringify(remainingBuffer));
      
    } catch (e) {
      console.error('Buffer sync failed', e);
    } finally {
      this.syncInProgress = false;
    }
  }
}
