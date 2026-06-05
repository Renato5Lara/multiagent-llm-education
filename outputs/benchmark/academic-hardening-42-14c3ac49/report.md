# Benchmark Report: academic-hardening-42-14c3ac49

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
| pass_at_1 | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| correction_rate | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| hallucination_reduction | swarm_full | 0.4336 | 0.0002 | 28.2915 | [0.4202, 0.4470] |
| grounding_score | swarm_full | 0.4336 | 0.0002 | 28.2915 | [0.4202, 0.4470] |
| misconception_coverage | swarm_full | 0.1336 | 0.0019 | 2.1820 | [0.0799, 0.1873] |
| bloom_alignment | swarm_full | 0.0136 | 0.1736 | 0.5680 | [-0.0074, 0.0346] |
| adaptation_impact | swarm_full | 0.0136 | 0.0963 | 0.8867 | [0.0002, 0.0270] |
| retrieval_confidence | swarm_full | 0.6332 | 0.0002 | 26.7737 | [0.6125, 0.6540] |
| execution_success | swarm_full | -0.0321 | 0.2265 | -0.5301 | [-0.0851, 0.0210] |
| sandbox_validation_success | swarm_full | -0.0321 | 0.2265 | -0.5301 | [-0.0851, 0.0210] |
| trajectory_length | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| consensus_confidence | swarm_full | 0.0136 | 0.0963 | 0.8867 | [0.0002, 0.0270] |
| pass_at_1 | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| correction_rate | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| hallucination_reduction | swarm_full | 0.0720 | 0.0002 | 3.6240 | [0.0546, 0.0895] |
| grounding_score | swarm_full | -0.0080 | 0.2568 | -0.4004 | [-0.0254, 0.0095] |
| misconception_coverage | swarm_full | 0.1120 | 0.0019 | 1.9220 | [0.0609, 0.1631] |
| bloom_alignment | swarm_full | -0.0080 | 0.5454 | -0.3012 | [-0.0311, 0.0152] |
| adaptation_impact | swarm_full | 0.0920 | 0.0002 | 4.6302 | [0.0746, 0.1095] |
| retrieval_confidence | swarm_full | 0.0175 | 0.0588 | 0.8052 | [-0.0016, 0.0366] |
| execution_success | swarm_full | -0.0221 | 0.2568 | -0.3737 | [-0.0740, 0.0298] |
| sandbox_validation_success | swarm_full | -0.0221 | 0.2568 | -0.3737 | [-0.0740, 0.0298] |
| trajectory_length | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| consensus_confidence | swarm_full | 0.0620 | 0.0002 | 3.1210 | [0.0446, 0.0795] |
| pass_at_1 | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| correction_rate | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| hallucination_reduction | swarm_full | -0.0017 | 0.8501 | -0.0914 | [-0.0180, 0.0146] |
| grounding_score | swarm_full | -0.0017 | 0.8501 | -0.0914 | [-0.0180, 0.0146] |
| misconception_coverage | swarm_full | -0.0017 | 0.9698 | -0.0266 | [-0.0576, 0.0542] |
| bloom_alignment | swarm_full | -0.0017 | 0.9097 | -0.0626 | [-0.0255, 0.0221] |
| adaptation_impact | swarm_full | -0.0017 | 0.8501 | -0.0914 | [-0.0180, 0.0146] |
| retrieval_confidence | swarm_full | 0.0067 | 0.6501 | 0.3019 | [-0.0128, 0.0262] |
| execution_success | swarm_full | 0.1700 | 0.0003 | 2.5283 | [0.1111, 0.2289] |
| sandbox_validation_success | swarm_full | 0.3500 | 0.0002 | 5.2054 | [0.2911, 0.4089] |
| trajectory_length | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| consensus_confidence | swarm_full | 0.0383 | 0.0015 | 2.0585 | [0.0220, 0.0546] |
| pass_at_1 | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| correction_rate | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| hallucination_reduction | swarm_full | -0.0044 | 0.5967 | -0.2362 | [-0.0207, 0.0119] |
| grounding_score | swarm_full | -0.0044 | 0.5967 | -0.2362 | [-0.0207, 0.0119] |
| misconception_coverage | swarm_full | -0.0044 | 0.5967 | -0.0662 | [-0.0625, 0.0537] |
| bloom_alignment | swarm_full | 0.1556 | 0.0002 | 5.6485 | [0.1315, 0.1798] |
| adaptation_impact | swarm_full | 0.4756 | 0.0002 | 25.5890 | [0.4593, 0.4919] |
| retrieval_confidence | swarm_full | 0.0036 | 0.7624 | 0.1381 | [-0.0193, 0.0265] |
| execution_success | swarm_full | -0.0286 | 0.2568 | -0.4375 | [-0.0860, 0.0287] |
| sandbox_validation_success | swarm_full | -0.0286 | 0.2568 | -0.4375 | [-0.0860, 0.0287] |
| trajectory_length | swarm_full | 0.0000 | 1.0000 | 0.0000 | [0.0000, 0.0000] |
| consensus_confidence | swarm_full | -0.0044 | 0.5967 | -0.2362 | [-0.0207, 0.0119] |
