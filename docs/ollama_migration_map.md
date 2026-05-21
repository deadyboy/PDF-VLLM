# Ollama to vLLM Migration Map

This project replaces Ollama multi-port scripts with one vLLM OpenAI-compatible
service on `127.0.0.1:8002`.

## Profiles

| Profile | Old entrypoint | Input | Cutter | Slices | Status |
|---|---|---|---|---|---|
| `jin` | `src2_vllm/main_last_vllm.py`, upgraded from `src2/main_last（金主任数据并行）.py` | `/data1/jianf/新提取pdf/180data` | `cutter_worker_jin.py` | `L/M/R`, plus `summary_*` | Implemented |
| `wang_record1` | `src/main（王主任数据一单）.py` | `/data1/jianf/新提取pdf/routed_data/data_record1` | `cutter_worker_wang_record1.py` | `1/2/3` | JSON extraction implemented |
| `wang_record2` | `src/main（王主任数据二单）.py` | `/data1/jianf/新提取pdf/routed_data/data_record2` | `cutter_worker_wang_record2.py` | `1/2/3/4/5`, plus header cache | JSON extraction implemented |

## Ignored Legacy Files

- `src/main_batch（单行）.py`: old serial/debug flow with inconsistent prompt formatting.
- `src/main_last2（王主任数据一单废除）.py`: marked deprecated in filename.
- `src/cutter_worker2（王主任数据二单废除）.py`: older four-part record2 cutter; current formal record2 is five-part.
- `src/main_record1.py`: contains useful merge-time-block ideas, but the runtime host string is polluted by Markdown and is not a safe source entrypoint.

## Conversion Rules

- Ollama `Client(host=http://127.0.0.1:<port>)` calls become shared vLLM async calls.
- Old per-GPU Ollama port scheduling becomes vLLM semaphore-based concurrency.
- Existing cutter geometry is preserved per profile, but OCR is forced to CPU and vLLM input images are capped at a long side of 1400 px.
- All outputs go under `/data1/jianf-vllm/runs/<run_id>/`; the old project paths are read-only inputs in config files.
