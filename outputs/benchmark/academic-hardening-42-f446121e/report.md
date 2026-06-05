# Benchmark Report: academic-hardening-42-f446121e

## Aggregate Metrics

| variant | metric | mean |
|---|---:|---:|
| single_agent_static | adaptation_impact | 0.2374 |
| single_agent_static | bloom_alignment | 0.4799 |
| single_agent_static | consensus_confidence | 0.4974 |
| single_agent_static | correction_rate | 0.0000 |
| single_agent_static | execution_success | 0.5354 |
| single_agent_static | grounding_score | 0.3674 |
| single_agent_static | hallucination_reduction | 0.1974 |
| single_agent_static | misconception_coverage | 0.4794 |
| single_agent_static | pass_at_1 | 0.0000 |
| single_agent_static | retrieval_confidence | 0.2144 |
| single_agent_static | sandbox_validation_success | 0.3554 |
| single_agent_static | trajectory_length | 2.0000 |
| swarm_full | adaptation_impact | 0.7985 |
| swarm_full | bloom_alignment | 0.7010 |
| swarm_full | consensus_confidence | 0.7885 |
| swarm_full | correction_rate | 0.0000 |
| swarm_full | execution_success | 0.7268 |
| swarm_full | grounding_score | 0.8485 |
| swarm_full | hallucination_reduction | 0.8385 |
| swarm_full | misconception_coverage | 0.7005 |
| swarm_full | pass_at_1 | 1.0000 |
| swarm_full | retrieval_confidence | 0.8268 |
| swarm_full | sandbox_validation_success | 0.7268 |
| swarm_full | trajectory_length | 1.0000 |
| swarm_no_memory | adaptation_impact | 0.7065 |
| swarm_no_memory | bloom_alignment | 0.7089 |
| swarm_no_memory | consensus_confidence | 0.7265 |
| swarm_no_memory | correction_rate | 0.0000 |
| swarm_no_memory | execution_success | 0.7490 |
| swarm_no_memory | grounding_score | 0.8564 |
| swarm_no_memory | hallucination_reduction | 0.7664 |
| swarm_no_memory | misconception_coverage | 0.5885 |
| swarm_no_memory | pass_at_1 | 1.0000 |
| swarm_no_memory | retrieval_confidence | 0.8093 |
| swarm_no_memory | sandbox_validation_success | 0.7490 |
| swarm_no_memory | trajectory_length | 1.0000 |
| swarm_no_retrieval | adaptation_impact | 0.7849 |
| swarm_no_retrieval | bloom_alignment | 0.6874 |
| swarm_no_retrieval | consensus_confidence | 0.7749 |
| swarm_no_retrieval | correction_rate | 0.0000 |
| swarm_no_retrieval | execution_success | 0.7589 |
| swarm_no_retrieval | grounding_score | 0.4149 |
| swarm_no_retrieval | hallucination_reduction | 0.4049 |
| swarm_no_retrieval | misconception_coverage | 0.5669 |
| swarm_no_retrieval | pass_at_1 | 1.0000 |
| swarm_no_retrieval | retrieval_confidence | 0.1936 |
| swarm_no_retrieval | sandbox_validation_success | 0.7589 |
| swarm_no_retrieval | trajectory_length | 1.0000 |
| swarm_no_reviewer | adaptation_impact | 0.8002 |
| swarm_no_reviewer | bloom_alignment | 0.7027 |
| swarm_no_reviewer | consensus_confidence | 0.7502 |
| swarm_no_reviewer | correction_rate | 0.0000 |
| swarm_no_reviewer | execution_success | 0.5568 |
| swarm_no_reviewer | grounding_score | 0.8502 |
| swarm_no_reviewer | hallucination_reduction | 0.8402 |
| swarm_no_reviewer | misconception_coverage | 0.7022 |
| swarm_no_reviewer | pass_at_1 | 1.0000 |
| swarm_no_reviewer | retrieval_confidence | 0.8201 |
| swarm_no_reviewer | sandbox_validation_success | 0.3768 |
| swarm_no_reviewer | trajectory_length | 1.0000 |
| swarm_static_pedagogy | adaptation_impact | 0.3229 |
| swarm_static_pedagogy | bloom_alignment | 0.5454 |
| swarm_static_pedagogy | consensus_confidence | 0.7929 |
| swarm_static_pedagogy | correction_rate | 0.0000 |
| swarm_static_pedagogy | execution_success | 0.7554 |
| swarm_static_pedagogy | grounding_score | 0.8529 |
| swarm_static_pedagogy | hallucination_reduction | 0.8429 |
| swarm_static_pedagogy | misconception_coverage | 0.7049 |
| swarm_static_pedagogy | pass_at_1 | 1.0000 |
| swarm_static_pedagogy | retrieval_confidence | 0.8232 |
| swarm_static_pedagogy | sandbox_validation_success | 0.7554 |
| swarm_static_pedagogy | trajectory_length | 1.0000 |

## Statistical Comparisons

| metric | treatment | delta | p | Cohen d | CI 95% |
|---|---|---:|---:|---:|---|
| pass_at_1 | swarm_full | 1.0000 | 0.0002 | 0.0000 | [1.0000, 1.0000] |
| correction_rate | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| hallucination_reduction | swarm_full | 0.6410 | 0.0002 | 43.0318 | [0.6280, 0.6541] |
| grounding_score | swarm_full | 0.4810 | 0.0002 | 32.2914 | [0.4680, 0.4941] |
| misconception_coverage | swarm_full | 0.2211 | 0.0003 | 3.6527 | [0.1680, 0.2741] |
| bloom_alignment | swarm_full | 0.2211 | 0.0002 | 8.5228 | [0.1983, 0.2438] |
| adaptation_impact | swarm_full | 0.5611 | 0.0002 | 37.6616 | [0.5480, 0.5741] |
| retrieval_confidence | swarm_full | 0.6124 | 0.0002 | 24.8031 | [0.5908, 0.6340] |
| execution_success | swarm_full | 0.1915 | 0.0002 | 3.1154 | [0.1376, 0.2453] |
| sandbox_validation_success | swarm_full | 0.3715 | 0.0002 | 6.0445 | [0.3176, 0.4253] |
| trajectory_length | swarm_full | -1.0000 | 0.0002 | 0.0000 | [-1.0000, -1.0000] |
| consensus_confidence | swarm_full | 0.2911 | 0.0002 | 19.5373 | [0.2780, 0.3041] |
