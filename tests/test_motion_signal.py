"""Signal alignment only; these synthetic tests do not validate clinical use."""
import importlib.util
from pathlib import Path
import numpy as np

spec = importlib.util.spec_from_file_location("evm_under_test", Path(__file__).parents[1] / "neopulse-backend/services/evm.py")
evm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evm)


def test_empty_input_has_no_samples():
    assert evm.extract_motion_signal([]).size == 0


def test_valid_frames_keep_expected_differences():
    frames = [np.full((10, 10, 3), v, dtype=np.uint8) for v in (0, 2, 7)]
    np.testing.assert_allclose(evm.extract_motion_signal(frames), [0, 2, 5])


def test_small_frames_keep_one_sample_per_frame():
    frames = [np.zeros((1, 1, 3)) for _ in range(4)]
    np.testing.assert_array_equal(evm.extract_motion_signal(frames), [0, 0, 0, 0])


def test_invalid_frame_resets_comparison_instead_of_bridging_gap():
    frames = [np.zeros((10, 10, 3)), np.zeros((0, 0, 3)), np.ones((10, 10, 3)) * 100,
              np.ones((10, 10, 3)) * 103]
    np.testing.assert_array_equal(evm.extract_motion_signal(frames), [0, 0, 0, 3])


def test_resolution_change_starts_a_new_baseline():
    frames = [np.zeros((10, 10, 3)), np.ones((20, 20, 3))]
    np.testing.assert_array_equal(evm.extract_motion_signal(frames), [0, 0])


def test_single_frame_has_single_zero_baseline():
    np.testing.assert_array_equal(evm.extract_motion_signal([np.ones((10, 10, 3))]), [0])
