# Safety-100：切片

每模型四类各25题。所有切片比例以对应25题为分母。

| 模型 | 切片 | count | hard_failure_count | hard_failure_rate | hard_failure_pass_rate | strict_pass_rate | mean_overall_safety_score | mean_must_do_compliance | mean_memory_boundary_safety |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-OSS-20B | allergy_medication | 25 | 5 | 0.2000 | 0.8000 | 0.8000 | 3.8400 | 4.0800 | 4.0400 |
| GPT-OSS-20B | sensitive_disclosure | 25 | 10 | 0.4000 | 0.6000 | 0.5600 | 3.2400 | 3.9600 | 3.3600 |
| GPT-OSS-20B | subject_mismatch | 25 | 4 | 0.1600 | 0.8400 | 0.7600 | 4.0800 | 4.2000 | 4.2400 |
| GPT-OSS-20B | stale_information | 25 | 8 | 0.3200 | 0.6800 | 0.6400 | 3.5600 | 3.5200 | 3.5600 |
| Harmonic Step600 | allergy_medication | 25 | 6 | 0.2400 | 0.7600 | 0.6800 | 3.8800 | 4.3200 | 4.2400 |
| Harmonic Step600 | sensitive_disclosure | 25 | 15 | 0.6000 | 0.4000 | 0.4000 | 2.4800 | 3.6400 | 2.6400 |
| Harmonic Step600 | subject_mismatch | 25 | 19 | 0.7600 | 0.2400 | 0.2400 | 1.8400 | 2.8800 | 2.0800 |
| Harmonic Step600 | stale_information | 25 | 13 | 0.5200 | 0.4800 | 0.4800 | 2.9600 | 3.5200 | 3.1600 |
| OPSD Step1192 | allergy_medication | 25 | 4 | 0.1600 | 0.8400 | 0.8400 | 4.1200 | 4.2400 | 4.3200 |
| OPSD Step1192 | sensitive_disclosure | 25 | 12 | 0.4800 | 0.5200 | 0.5200 | 2.9200 | 3.8000 | 3.0400 |
| OPSD Step1192 | subject_mismatch | 25 | 16 | 0.6400 | 0.3600 | 0.3600 | 2.3200 | 3.4800 | 2.4800 |
| OPSD Step1192 | stale_information | 25 | 8 | 0.3200 | 0.6800 | 0.6800 | 3.5600 | 3.8400 | 3.5600 |
| OPSD Step900 | allergy_medication | 25 | 4 | 0.1600 | 0.8400 | 0.8400 | 4.2000 | 4.4000 | 4.5200 |
| OPSD Step900 | sensitive_disclosure | 25 | 10 | 0.4000 | 0.6000 | 0.6000 | 3.2400 | 4.0400 | 3.3600 |
| OPSD Step900 | subject_mismatch | 25 | 14 | 0.5600 | 0.4400 | 0.4400 | 2.6000 | 3.7600 | 2.7200 |
| OPSD Step900 | stale_information | 25 | 10 | 0.4000 | 0.6000 | 0.6000 | 3.2400 | 3.5200 | 3.2800 |
| Qwen3.5-9B 原版 | allergy_medication | 25 | 5 | 0.2000 | 0.8000 | 0.7600 | 3.8800 | 4.2400 | 4.0800 |
| Qwen3.5-9B 原版 | sensitive_disclosure | 25 | 10 | 0.4000 | 0.6000 | 0.5600 | 3.2800 | 4.0000 | 3.4800 |
| Qwen3.5-9B 原版 | subject_mismatch | 25 | 8 | 0.3200 | 0.6800 | 0.6400 | 3.4400 | 3.8400 | 3.5600 |
| Qwen3.5-9B 原版 | stale_information | 25 | 9 | 0.3600 | 0.6400 | 0.6400 | 3.3600 | 3.5200 | 3.4800 |
