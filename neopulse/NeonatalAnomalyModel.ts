import { loadTensorflowModel, TensorflowModel } from 'react-native-fast-tflite';

export type AnomalyLabel = 'NORMAL' | 'CAUTION' | 'EMERGENCY';

export interface InferenceResult {
  label: AnomalyLabel;
  confidence: number;
  hr_bpm: number;
  rr_bpm: number;
}

export type InferenceCallback = (result: InferenceResult | null, error?: Error) => void;

/**
 * TFLite Inference Wrapper for React Native
 * Assumes the model outputs:
 *  - Output 0: Float32Array[3] -> [prob_normal, prob_caution, prob_emergency]
 *  - Output 1: Float32Array[2] -> [hr_bpm, rr_bpm]
 * (Or a single concatenated Float32Array[5])
 */
export class NeonatalInferenceWrapper {
  private model: TensorflowModel | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private latestInput: Float32Array | null = null;
  private isInferencing: boolean = false;
  private callback: InferenceCallback | null = null;
  
  /**
   * Loads the quantized TFLite model from the app bundle.
   * @param modelSource - e.g. require('./assets/neonatal_quant.tflite')
   */
  public async loadModel(modelSource: any): Promise<void> {
    try {
      this.model = await loadTensorflowModel(modelSource);
    } catch (e) {
      throw new Error(`Model load failure: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  /**
   * Updates the buffer with the latest frame data.
   * Expects shape: [1, 60, 4] -> 240 elements.
   */
  public setLatestInput(input: Float32Array) {
    if (input.length !== 240) {
      console.warn(`Input shape mismatch. Expected 240 elements [1, 60, 4], got ${input.length}`);
    }
    this.latestInput = input;
  }

  /**
   * Starts a 1Hz loop that dispatches the most recent data to the background inference thread.
   */
  public startInferenceLoop(callback: InferenceCallback) {
    this.callback = callback;
    
    // Call result callback at exactly 1Hz
    this.timer = setInterval(() => {
      this.runInferenceTask();
    }, 1000);
  }

  public stopInferenceLoop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this.callback = null;
  }

  private async runInferenceTask() {
    if (!this.model) {
      this.callback?.(null, new Error("Model not loaded. Call loadModel() first."));
      return;
    }
    
    if (!this.latestInput) {
      return; // Awaiting first input chunk
    }
    
    // Prevent overlapping inferences if the device is severely bottlenecked
    if (this.isInferencing) {
      return;
    }
    
    this.isInferencing = true;
    
    try {
      const inputBuffer = this.latestInput;
      
      // react-native-fast-tflite `run()` executes on a native C++ background thread via JSI
      const inferencePromise = this.model.run([inputBuffer]);
      
      // 200ms Timeout constraint
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error("INFERENCE_TIMEOUT: Model execution took >200ms")), 200);
      });
      
      // Race the background execution against the strict 200ms limit
      const outputs = await Promise.race([inferencePromise, timeoutPromise]) as any[];
      
      let probs: Float32Array;
      let metrics: Float32Array;
      
      // Parse multi-tensor or concatenated tensor output
      if (outputs.length >= 2) {
        probs = outputs[0] as Float32Array;
        metrics = outputs[1] as Float32Array;
      } else {
        const outArray = outputs[0] as Float32Array;
        probs = outArray.slice(0, 3);
        metrics = outArray.slice(3, 5);
      }
      
      const labels: AnomalyLabel[] = ['NORMAL', 'CAUTION', 'EMERGENCY'];
      
      // Argmax
      let maxIdx = 0;
      let maxProb = probs[0];
      for (let i = 1; i < 3; i++) {
        if (probs[i] > maxProb) {
          maxProb = probs[i];
          maxIdx = i;
        }
      }
      
      let predictedLabel = labels[maxIdx];
      let confidence = maxProb;
      
      // Low-confidence Fallback rule
      if (confidence < 0.6) {
        predictedLabel = 'CAUTION';
      }
      
      const result: InferenceResult = {
        label: predictedLabel,
        confidence: confidence,
        hr_bpm: metrics[0],
        rr_bpm: metrics[1]
      };
      
      this.callback?.(result);
      
    } catch (error) {
      this.callback?.(null, error instanceof Error ? error : new Error(String(error)));
    } finally {
      this.isInferencing = false;
    }
  }
}
