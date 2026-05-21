# ICU vLLM Extraction Pipeline

This workspace contains only the vLLM extraction pipeline. The old project is
used as a read-only image source through `config/default.toml`.

## Commands

Start vLLM:

```bash
cd /data1/jianf-vllm
conda activate vllm
bash scripts/start_vllm_server.sh
```

Run extraction:

```bash
cd /data1/jianf-vllm
/home/jianf/miniconda3/envs/vllm/bin/python -m icu_vllm.run \
  --config config/default.toml \
  --run-id "$(date +%Y%m%d-%H%M%S)-180data"
```

Run Wang director record types:

```bash
/home/jianf/miniconda3/envs/vllm/bin/python -m icu_vllm.run \
  --config config/wang_record1.toml \
  --run-id "$(date +%Y%m%d-%H%M%S)-wang-record1"

/home/jianf/miniconda3/envs/vllm/bin/python -m icu_vllm.run \
  --config config/wang_record2.toml \
  --run-id "$(date +%Y%m%d-%H%M%S)-wang-record2"
```

Resume an interrupted run:

```bash
/home/jianf/miniconda3/envs/vllm/bin/python -m icu_vllm.run \
  --config config/default.toml \
  --run-id <existing-run-id> \
  --resume
```

Merge JSON into Excel:

```bash
/home/jianf/miniconda3/envs/vllm/bin/python -m icu_vllm.merge \
  --run-dir /data1/jianf-vllm/runs/<run-id>
```

Inspect a run:

```bash
/home/jianf/miniconda3/envs/vllm/bin/python -m icu_vllm.inspect \
  --config config/default.toml \
  --run-dir /data1/jianf-vllm/runs/<run-id>
```

Smoke test one image:

```bash
/home/jianf/miniconda3/envs/vllm/bin/python -m icu_vllm.run \
  --config config/default.toml \
  --run-id smoke-0010016667 \
  --patient-id 0010016667 \
  --limit 1
```
