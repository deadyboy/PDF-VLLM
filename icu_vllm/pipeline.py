from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .config import PipelineConfig, RunDirs
from .json_utils import normalize_nulls, parse_model_json
from .prompts import PROMPT_HEADER, PROMPT_L, PROMPT_M, PROMPT_R, PROMPT_SUMMARY


class ExtractionPipeline:
    def __init__(self, cfg: PipelineConfig, run_dirs: RunDirs, resume: bool = False):
        self.cfg = cfg
        self.run_dirs = run_dirs
        self.resume = resume
        self.client = AsyncOpenAI(
            base_url=cfg.vllm_base_url,
            api_key=cfg.vllm_api_key,
            timeout=cfg.timeout_seconds,
        )
        self.llm_semaphore = asyncio.Semaphore(cfg.max_concurrent_llm)
        self.cut_semaphore = asyncio.Semaphore(cfg.max_concurrent_cut)
        self.img_semaphore = asyncio.Semaphore(cfg.max_concurrent_img)

    def call_paddle_env_to_cut(self, img_path: Path, output_dir: Path) -> None:
        worker_script = Path(__file__).with_name("cutter_worker_jin.py")
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = ""

        result = subprocess.run(
            [str(self.cfg.ocr_python), str(worker_script), "--img", str(img_path), "--out", str(output_dir)],
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"切割崩溃。\nstderr:\n{result.stderr}")
        if not output_dir.exists() or not list(output_dir.glob("*.png")):
            raise RuntimeError(f"未生成图片！可能未识别到表格。\nstderr:\n{result.stderr}")

    @staticmethod
    def encode_image_base64(img_path: Path) -> str:
        return base64.b64encode(img_path.read_bytes()).decode("utf-8")

    async def extract_single_part(self, img_path: Path, prompt_text: str, retries: int = 5) -> dict[str, Any]:
        if not img_path.exists():
            return {"_error": "文件不存在"}

        txt_path = img_path.with_suffix(".txt")
        ocr_text = txt_path.read_text(encoding="utf-8").strip() if txt_path.exists() else ""
        dynamic_prompt = prompt_text
        if ocr_text:
            dynamic_prompt += f"""

=========================================
【OCR 辅助防漏字典】
底层扫描器在当前切片中识别到了以下零散的文本碎片：
[{ocr_text}]

【使用规则】
1. 你依然需要亲自"看图识字"，严格依据图片中表头的垂直对齐关系来提取数据。
2. 上述字典仅为无序的文本碎片，请作为参考，用来核对你是否有漏字、错字（例如极易漏掉的短小字符或标点）。
3. 如果图片中看到的与字典一致，请务必完整提取，绝不遗漏！
=========================================
"""

        img_b64 = self.encode_image_base64(img_path)
        raw = ""
        for attempt in range(retries):
            try:
                async with self.llm_semaphore:
                    response = await self.client.chat.completions.create(
                        model=self.cfg.model_name,
                        messages=[{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": dynamic_prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                            ],
                        }],
                        temperature=0.0,
                        max_tokens=8192,
                        stop=["<|im_end|>", "<|endoftext|>"],
                    )
                raw = response.choices[0].message.content or ""
                return parse_model_json(raw)
            except Exception as exc:
                if attempt == retries - 1:
                    return {"_error": "解析彻底失败", "_raw": raw or f"【底层服务通信失败】: {exc}"}
                await asyncio.sleep(1)
        return {"_error": "重试多次均失败"}

    async def extract_patient_info_once(self, slice_dir: Path, img_name: str) -> None:
        patient_id = img_name.split("_")[0]
        cache_file = self.run_dirs.patient_cache_dir / f"{patient_id}.json"
        if cache_file.exists():
            return
        header_img_path = slice_dir / "_header_info.png"
        if not header_img_path.exists():
            return
        patient_data = await self.extract_single_part(header_img_path, PROMPT_HEADER)
        if "_error" not in patient_data:
            cache_file.write_text(json.dumps(patient_data, ensure_ascii=False, indent=2), encoding="utf-8")

    async def process_three_columns_batch(self, slice_dir: Path, output_json: Path, img_name: str) -> None:
        l_files = sorted(slice_dir.glob("block_*_L.png"))
        if not l_files:
            raise RuntimeError(f"在 {slice_dir} 中未找到 L 切片文件。")

        error_log_file = self.run_dirs.logs_dir / "llm_json_errors_log.txt"

        async def process_one_block(l_img: Path) -> dict[str, Any]:
            prefix = l_img.stem.replace("_L", "")
            m_img = slice_dir / f"{prefix}_M.png"
            r_img = slice_dir / f"{prefix}_R.png"
            data_l, data_m, data_r = await asyncio.gather(
                self.extract_single_part(l_img, PROMPT_L),
                self.extract_single_part(m_img, PROMPT_M),
                self.extract_single_part(r_img, PROMPT_R),
            )
            if "_raw" in data_l or "_raw" in data_m or "_raw" in data_r:
                with error_log_file.open("a", encoding="utf-8") as f:
                    f.write(f"\n{'=' * 50}\n")
                    f.write(f"发现错误: 图片 {img_name} -> 块 {prefix}\n")
                    if "_raw" in data_l:
                        f.write(f"【左侧部分返回】:\n{data_l['_raw']}\n\n")
                    if "_raw" in data_m:
                        f.write(f"【中间部分返回】:\n{data_m['_raw']}\n\n")
                    if "_raw" in data_r:
                        f.write(f"【右侧部分返回】:\n{data_r['_raw']}\n\n")
            merged = {**data_l, **data_m, **data_r}
            merged.pop("_raw", None)
            merged["_block_id"] = prefix
            return normalize_nulls(merged)

        results = list(await asyncio.gather(*(process_one_block(path) for path in l_files)))

        async def process_summary(s_img: Path) -> dict[str, Any]:
            prefix = s_img.stem
            data_summary = await self.extract_single_part(s_img, PROMPT_SUMMARY)
            if "_raw" in data_summary:
                with error_log_file.open("a", encoding="utf-8") as f:
                    f.write(f"\n{'=' * 50}\n")
                    f.write(f"小时小结错误: 图片 {img_name} -> {prefix}\n")
                    f.write(f"【返回】:\n{data_summary['_raw']}\n\n")
                data_summary.pop("_raw", None)
            data_summary["_block_id"] = prefix
            return normalize_nulls(data_summary)

        summary_files = sorted(slice_dir.glob("summary_*.png"))
        if summary_files:
            results.extend(await asyncio.gather(*(process_summary(path) for path in summary_files)))

        output_json.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    async def process_single_image(self, img_file: Path) -> str:
        json_path = self.run_dirs.results_json_dir / f"{img_file.stem}_result.json"
        if self.resume and json_path.exists():
            return f"SKIPPED {img_file.name}"

        temp_slice_dir = self.run_dirs.logs_dir / f"temp_{img_file.stem}"
        try:
            async with self.cut_semaphore:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.call_paddle_env_to_cut, img_file, temp_slice_dir)
            await self.extract_patient_info_once(temp_slice_dir, img_file.name)
            await self.process_three_columns_batch(temp_slice_dir, json_path, img_file.name)
            return f"SUCCESS {img_file.name}"
        except Exception as exc:
            if temp_slice_dir.exists():
                for dbg_img in temp_slice_dir.glob("debug_*.png"):
                    shutil.copy(dbg_img, self.run_dirs.failed_debug_dir / f"{img_file.stem}_{dbg_img.name}")
            return f"FAILED {img_file.name} {exc}"
        finally:
            if temp_slice_dir.exists():
                shutil.rmtree(temp_slice_dir, ignore_errors=True)

    async def batch_process_parallel(
        self,
        patient_id: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        image_files = sorted(
            list(self.cfg.input_dir.glob("*.png"))
            + list(self.cfg.input_dir.glob("*.jpg"))
            + list(self.cfg.input_dir.glob("*.jpeg"))
        )
        if patient_id:
            image_files = [p for p in image_files if p.name.startswith(f"{patient_id}_")]
        if limit is not None:
            image_files = image_files[:limit]

        start = time.time()

        async def throttled_process(img_file: Path) -> str:
            async with self.img_semaphore:
                return await self.process_single_image(img_file)

        results = await asyncio.gather(*(throttled_process(img) for img in image_files))
        elapsed = time.time() - start
        manifest = {
            "run_id": self.run_dirs.run_id,
            "input_dir": str(self.cfg.input_dir),
            "result_dir": str(self.run_dirs.results_json_dir),
            "patient_cache_dir": str(self.run_dirs.patient_cache_dir),
            "excel_dir": str(self.run_dirs.excel_dir),
            "image_count": len(image_files),
            "success": sum(1 for r in results if r.startswith("SUCCESS")),
            "skipped": sum(1 for r in results if r.startswith("SKIPPED")),
            "failed": sum(1 for r in results if r.startswith("FAILED")),
            "elapsed_seconds": round(elapsed, 3),
            "messages": results,
        }
        self.run_dirs.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
