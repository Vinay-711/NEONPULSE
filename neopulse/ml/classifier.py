"""
NeoPulse AI — Temporal CNN Classifier (Phase 2)
=================================================
A lightweight 1D temporal CNN that classifies neonatal vital sign
patterns directly from the EVM signal windows.

Architecture
------------
Input:  (T=90 timesteps, 2 channels) — green & motion signal window
        at 30 fps → 3-second sliding window

Output: softmax over 4 classes:
  0 — Normal
  1 — Tachycardia   (HR > 160 bpm)
  2 — Bradycardia   (HR < 100 bpm)
  3 — Tachypnea     (RR > 60 brpm)

This module provides:
  1. Model architecture definition (Keras / TensorFlow)
  2. Synthetic training data generator (for demo training without real data)
  3. TFLite export + quantization for edge deployment
  4. TFLiteClassifier — drop-in replacement for threshold-based classify_vitals()

Why a CNN over the Welch PSD approach?
  - Can detect transient arrhythmias that frequency averaging misses
  - Learns nonlinear patterns (irregular rhythm, combined abnormalities)
  - Once trained on labelled clinical data, is more robust to motion artifacts
  - The TFLite model is ~50–200 KB, runs at ~1 ms per inference on mobile

Usage
-----
  # Training (run once, generates model.tflite)
  python -m neopulse.ml.classifier --train --epochs 30

  # Inference in the live pipeline:
  clf = TFLiteClassifier("model.tflite")
  label, confidence = clf.predict(green_window, motion_window)
"""

import numpy as np
import os
import argparse
from pathlib import Path

WINDOW_SIZE  = 90    # 3 seconds at 30 fps
N_CHANNELS   = 2     # green signal + motion signal
N_CLASSES    = 4
CLASS_NAMES  = ["Normal", "Tachycardia", "Bradycardia", "Tachypnea"]
MODEL_PATH   = Path(__file__).parent / "model.tflite"


# ---------------------------------------------------------------------------
# 1. Synthetic data generator
# ---------------------------------------------------------------------------

def _make_sample(label: int, fps: float = 30.0, noise_std: float = 0.003) -> np.ndarray:
    """
    Generate one synthetic (WINDOW_SIZE, 2) signal window for a given class.

    Green channel carries rPPG (heart rate signal).
    Motion channel carries respiration signal.

    Returns shape (WINDOW_SIZE, 2) float32.
    """
    t = np.arange(WINDOW_SIZE) / fps
    rng = np.random.default_rng()

    if label == 0:   # Normal: HR 110–155 bpm, RR 30–55 brpm
        hr_hz = rng.uniform(110, 155) / 60
        rr_hz = rng.uniform(30, 55) / 60
    elif label == 1: # Tachycardia: HR 165–210 bpm
        hr_hz = rng.uniform(165, 210) / 60
        rr_hz = rng.uniform(30, 55) / 60
    elif label == 2: # Bradycardia: HR 55–95 bpm
        hr_hz = rng.uniform(55, 95) / 60
        rr_hz = rng.uniform(30, 55) / 60
    else:            # Tachypnea: RR 65–80 brpm
        hr_hz = rng.uniform(110, 155) / 60
        rr_hz = rng.uniform(65, 80) / 60

    amp_g  = rng.uniform(0.015, 0.040)
    amp_m  = rng.uniform(0.004, 0.012)
    phase_g = rng.uniform(0, 2 * np.pi)
    phase_m = rng.uniform(0, 2 * np.pi)

    green  = amp_g * np.sin(2 * np.pi * hr_hz * t + phase_g)
    motion = amp_m * np.sin(2 * np.pi * rr_hz * t + phase_m)

    # Add realistic drift and noise
    drift  = rng.uniform(-0.02, 0.02) * np.linspace(0, 1, WINDOW_SIZE)
    green  = green + drift + rng.normal(0, noise_std, WINDOW_SIZE)
    motion = motion + rng.normal(0, noise_std * 0.3, WINDOW_SIZE)

    # Normalise each channel to zero mean / unit variance
    green  = (green  - green.mean())  / (green.std()  + 1e-8)
    motion = (motion - motion.mean()) / (motion.std() + 1e-8)

    return np.stack([green, motion], axis=-1).astype(np.float32)


def generate_dataset(n_per_class: int = 2000) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate a balanced synthetic dataset.
    Returns (X, y) where X.shape = (N, WINDOW_SIZE, 2), y.shape = (N,)
    """
    print(f"Generating {n_per_class * N_CLASSES} synthetic training samples...")
    X, y = [], []
    for label in range(N_CLASSES):
        for _ in range(n_per_class):
            X.append(_make_sample(label))
            y.append(label)
    X = np.array(X)
    y = np.array(y)
    # Shuffle
    idx = np.random.permutation(len(X))
    return X[idx], y[idx]


# ---------------------------------------------------------------------------
# 2. Model architecture
# ---------------------------------------------------------------------------

def build_model():
    """
    Build a lightweight 1D temporal CNN.

    Architecture:
      Input → Conv1D(32,7) → BN → ReLU
            → Conv1D(64,5) → BN → ReLU → GlobalAvgPool
            → Dense(64) → Dropout(0.3)
            → Dense(4, softmax)

    ~45K parameters — fast enough for TFLite int8 at <2 ms on Cortex-A55.
    """
    try:
        import tensorflow as tf
        from tensorflow import keras
    except ImportError:
        raise ImportError(
            "TensorFlow is required for model training.\n"
            "Install: pip install tensorflow\n"
            "For edge deploy only (no training), tflite-runtime is sufficient."
        )

    inp = keras.Input(shape=(WINDOW_SIZE, N_CHANNELS), name="signal_window")

    x = keras.layers.Conv1D(32, kernel_size=7, padding="same", use_bias=False)(inp)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)
    x = keras.layers.MaxPooling1D(pool_size=2)(x)

    x = keras.layers.Conv1D(64, kernel_size=5, padding="same", use_bias=False)(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)
    x = keras.layers.MaxPooling1D(pool_size=2)(x)

    x = keras.layers.Conv1D(128, kernel_size=3, padding="same", use_bias=False)(x)
    x = keras.layers.BatchNormalization()(x)
    x = keras.layers.Activation("relu")(x)

    x = keras.layers.GlobalAveragePooling1D()(x)
    x = keras.layers.Dense(64, activation="relu")(x)
    x = keras.layers.Dropout(0.3)(x)
    out = keras.layers.Dense(N_CLASSES, activation="softmax", name="class_probs")(x)

    model = keras.Model(inputs=inp, outputs=out, name="NeoPulseCNN")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


# ---------------------------------------------------------------------------
# 3. Training + TFLite export
# ---------------------------------------------------------------------------

def train_and_export(
    n_per_class: int = 2000,
    epochs: int = 30,
    batch_size: int = 64,
    output_path: Path = MODEL_PATH,
    quantize: bool = True,
):
    """
    Train on synthetic data and export a TFLite model.

    For production, replace generate_dataset() with real labelled
    neonatal video data (e.g. from PhysioNet or a hospital partner).
    """
    try:
        import tensorflow as tf
    except ImportError:
        raise ImportError("pip install tensorflow")

    X, y = generate_dataset(n_per_class)
    split = int(len(X) * 0.85)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"Train: {len(X_train)} samples  |  Val: {len(X_val)} samples")
    print(f"Classes: {CLASS_NAMES}")

    model = build_model()
    model.summary()

    callbacks = [
        tf.keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=3, verbose=1),
    ]

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1,
    )

    val_acc = max(history.history["val_accuracy"])
    print(f"\nBest validation accuracy: {val_acc:.1%}")

    # --- TFLite conversion ---
    print(f"\nConverting to TFLite {'(int8 quantized)' if quantize else '(float32)'}...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)

    if quantize:
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        # Representative dataset for calibration
        def representative_data():
            for i in range(min(200, len(X_train))):
                yield [X_train[i:i+1]]
        converter.representative_dataset = representative_data
        converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        converter.inference_input_type  = tf.int8
        converter.inference_output_type = tf.int8

    tflite_model = converter.convert()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(tflite_model)

    size_kb = output_path.stat().st_size / 1024
    print(f"Saved: {output_path}  ({size_kb:.1f} KB)")
    return history


# ---------------------------------------------------------------------------
# 4. TFLite inference — the edge classifier
# ---------------------------------------------------------------------------

class TFLiteClassifier:
    """
    Loads a NeoPulse TFLite model and runs inference on signal windows.

    This is the production classifier that runs on-device (phone / RPi).
    It requires only tflite-runtime (~2 MB), not full TensorFlow.

    Parameters
    ----------
    model_path : str or Path
        Path to the .tflite model file.
    use_full_tf : bool
        If True, use tensorflow.lite instead of tflite_runtime (for dev).

    Usage
    -----
    clf = TFLiteClassifier("model.tflite")
    label, confidence = clf.predict(green_window, motion_window)
    """

    def __init__(self, model_path: str | Path = MODEL_PATH, use_full_tf: bool = False):
        self.model_path = Path(model_path)
        self._quantized = False

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"TFLite model not found: {self.model_path}\n"
                f"Run: python -m neopulse.ml.classifier --train"
            )

        # Load interpreter
        try:
            if use_full_tf:
                raise ImportError  # force tflite_runtime path
            import tflite_runtime.interpreter as tflite
            self._interp = tflite.Interpreter(model_path=str(self.model_path))
        except ImportError:
            try:
                import tensorflow as tf
                self._interp = tf.lite.Interpreter(model_path=str(self.model_path))
            except ImportError:
                raise ImportError(
                    "Install tflite-runtime (edge) or tensorflow (dev):\n"
                    "  pip install tflite-runtime\n"
                    "  pip install tensorflow"
                )

        self._interp.allocate_tensors()
        self._input_details  = self._interp.get_input_details()
        self._output_details = self._interp.get_output_details()

        # Detect quantized model
        inp_dtype = self._input_details[0]["dtype"]
        self._quantized = (inp_dtype == np.int8)
        if self._quantized:
            self._inp_scale, self._inp_zp  = self._input_details[0]["quantization"]
            self._out_scale, self._out_zp  = self._output_details[0]["quantization"]

    def _preprocess(self, green: np.ndarray, motion: np.ndarray) -> np.ndarray:
        """Stack, normalise, and window-slice to (1, WINDOW_SIZE, 2)."""
        # Take the last WINDOW_SIZE samples
        n = min(len(green), len(motion), WINDOW_SIZE)
        g = green[-n:];  m = motion[-n:]
        # Pad with zeros if shorter
        if n < WINDOW_SIZE:
            g = np.pad(g, (WINDOW_SIZE - n, 0))
            m = np.pad(m, (WINDOW_SIZE - n, 0))
        # Normalise
        g = (g - g.mean()) / (g.std() + 1e-8)
        m = (m - m.mean()) / (m.std() + 1e-8)
        window = np.stack([g, m], axis=-1).astype(np.float32)
        return window[np.newaxis, ...]  # (1, T, 2)

    def predict(
        self,
        green: np.ndarray,
        motion: np.ndarray,
    ) -> tuple[str, float, np.ndarray]:
        """
        Run inference on a signal window.

        Parameters
        ----------
        green  : 1D array of green channel values (len >= WINDOW_SIZE recommended)
        motion : 1D array of motion magnitude values

        Returns
        -------
        label      : str — predicted class name
        confidence : float — softmax probability of predicted class
        probs      : np.ndarray shape (4,) — full class probabilities
        """
        window = self._preprocess(green, motion)

        if self._quantized:
            window_q = (window / self._inp_scale + self._inp_zp).astype(np.int8)
            self._interp.set_tensor(self._input_details[0]["index"], window_q)
            self._interp.invoke()
            out_q = self._interp.get_tensor(self._output_details[0]["index"])
            probs = (out_q.astype(np.float32) - self._out_zp) * self._out_scale
        else:
            self._interp.set_tensor(self._input_details[0]["index"], window)
            self._interp.invoke()
            probs = self._interp.get_tensor(self._output_details[0]["index"])

        probs = probs.flatten()
        # Softmax safety (in case of quantization drift)
        probs = np.exp(probs - probs.max())
        probs /= probs.sum()

        idx = int(np.argmax(probs))
        return CLASS_NAMES[idx], float(probs[idx]), probs


# ---------------------------------------------------------------------------
# 5. Sliding window buffer — integrates with the live pipeline
# ---------------------------------------------------------------------------

class SlidingWindowBuffer:
    """
    Accumulates EVM signal samples and runs the CNN classifier
    every `stride` new samples (default: 15 = 0.5s at 30 fps).

    Usage in the main loop
    ----------------------
    buf = SlidingWindowBuffer(classifier)
    # on each frame:
    result = buf.push(green_val, motion_val)
    if result:
        label, confidence, probs = result
    """

    def __init__(self, classifier: TFLiteClassifier, stride: int = 15):
        self.clf    = classifier
        self.stride = stride
        self._green  = []
        self._motion = []
        self._counter = 0
        self.last_result = None

    def push(self, green_val: float, motion_val: float):
        self._green.append(green_val)
        self._motion.append(motion_val)
        self._counter += 1

        if len(self._green) >= WINDOW_SIZE and self._counter >= self.stride:
            self._counter = 0
            g = np.array(self._green[-WINDOW_SIZE:])
            m = np.array(self._motion[-WINDOW_SIZE:])
            self.last_result = self.clf.predict(g, m)
            return self.last_result

        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NeoPulse CNN Classifier")
    parser.add_argument("--train",        action="store_true", help="Train and export TFLite model")
    parser.add_argument("--epochs",       type=int, default=30)
    parser.add_argument("--n-per-class",  type=int, default=2000)
    parser.add_argument("--no-quantize",  action="store_true", help="Export float32 model (larger, for debugging)")
    parser.add_argument("--test",         action="store_true", help="Test the exported model with synthetic data")
    args = parser.parse_args()

    if args.train:
        train_and_export(
            n_per_class=args.n_per_class,
            epochs=args.epochs,
            quantize=not args.no_quantize,
        )

    if args.test:
        print("\nTesting TFLite classifier on synthetic samples...")
        clf = TFLiteClassifier()
        correct = 0
        total   = 40
        for label in range(N_CLASSES):
            for _ in range(total // N_CLASSES):
                sample = _make_sample(label)
                g, m   = sample[:, 0], sample[:, 1]
                pred, conf, _ = clf.predict(g, m)
                ok = pred == CLASS_NAMES[label]
                if ok:
                    correct += 1
        print(f"Accuracy on {total} synthetic samples: {correct}/{total} = {correct/total:.0%}")
