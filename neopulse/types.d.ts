declare module 'react-native-fast-tflite' {
  export interface TensorflowModel {
    /**
     * Run inference on the given inputs.
     * @param inputs Array of input tensors (e.g. Float32Array)
     * @returns Array of output tensors
     */
    run(inputs: any[]): Promise<any[]>;
  }

  /**
   * Load a TensorFlow Lite model from the given source.
   * @param modelSource The require() path or URL to the model
   * @returns A promise that resolves to the loaded model
   */
  export function loadTensorflowModel(modelSource: any): Promise<TensorflowModel>;
}
