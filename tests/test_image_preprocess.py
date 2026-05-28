import cv2
import numpy as np

from icu_vllm.image_preprocess import (
    VARIANT_FILENAMES,
    adaptive_binary,
    clahe_enhance,
    line_removed,
    upscale_with_border,
    write_observation_preprocess_variants,
)


def _sample_grid_image() -> np.ndarray:
    image = np.full((80, 120, 3), 255, dtype=np.uint8)
    cv2.line(image, (0, 20), (119, 20), (0, 0, 0), 2)
    cv2.line(image, (40, 0), (40, 79), (0, 0, 0), 2)
    cv2.putText(image, "APTT43.6", (8, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return image


def test_upscale_with_border_scales_and_adds_white_border():
    image = np.full((10, 20, 3), 127, dtype=np.uint8)

    result = upscale_with_border(image, scale=2, border=4)

    assert result.shape == (28, 48, 3)
    assert result[0, 0].tolist() == [255, 255, 255]


def test_line_removed_reduces_long_table_lines_without_changing_shape():
    image = _sample_grid_image()
    before_dark = int(np.sum(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) < 40))

    result = line_removed(image)
    after_dark = int(np.sum(cv2.cvtColor(result, cv2.COLOR_BGR2GRAY) < 40))

    assert result.shape == image.shape
    assert after_dark < before_dark


def test_clahe_and_binary_return_three_channel_images():
    image = _sample_grid_image()

    clahe = clahe_enhance(image)
    binary = adaptive_binary(image)

    assert clahe.shape == image.shape
    assert binary.shape == image.shape
    assert set(np.unique(binary.reshape(-1, 3)[:, 0])).issubset({0, 255})


def test_write_observation_preprocess_variants_outputs_all_images(tmp_path):
    image_path = tmp_path / "block_00_col_observation.png"
    cv2.imwrite(str(image_path), _sample_grid_image())

    manifest = write_observation_preprocess_variants(
        raw_col_path=image_path,
        output_dir=tmp_path,
        block_id="block_00",
    )

    assert set(manifest["variants"]) == set(VARIANT_FILENAMES)
    for filename in VARIANT_FILENAMES.values():
        assert (tmp_path / filename.format(block_id="block_00")).exists()
    assert (tmp_path / "block_00_obs_preprocess_overlay.png").exists()
