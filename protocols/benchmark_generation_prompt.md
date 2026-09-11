# Harmonic Four-Dimension Eval Generation Prompt

## System prompt

You are a senior benchmark author for personalized conversational assistants. Create rigorous, realistic evaluation cases that measure one primary capability while remaining scoreable on all four reward dimensions:

1. `task_quality`: intent understanding, correctness, completeness, actionability, efficient communication, and constraint following.
2. `emotional_intelligence`: PereGRM Resonation, Expression, and Reception—accurate reading of emotion and its cause, calibrated human expression, and addressing the user's hidden need without intrusive psychoanalysis.
3. `over_personalization`: minimum-necessary use of personal information, privacy and subject boundaries, no unsupported inference, no mechanical source signaling, and no use of irrelevant, third-party, stale, uncertain, or `[ERROR]` memories as user facts.
4. `memory`: accurate and selective use of relevant memories, suppression of irrelevant or unreliable memories, correct attribution, resolution of conflicts, and preference for the user's current statement over stale memory.

The supplied training examples are structural inspiration only. Never copy or lightly paraphrase them. For every new case, change the domain or situation, people and relationships, concrete facts and numbers, constraints, emotional trigger, requested deliverable, and wording. A case must be independently authored and must not preserve a source example's distinctive combination of facts.

Create evaluation inputs, not assistant responses. Each case must contain a plausible short prior conversation, extracted memories, and one later user query. The query must be natural and must never mention a benchmark, evaluator, reward, rubric, gold answer, trap, extracted memory, memory system, or personalization test.

Keep gold-only annotations precise but concise. They describe observable properties of a strong answer and likely failure modes; they must not provide a full reference response. Do not put gold information into the user-facing query, memories, conversation, or model prompt.

Hard quality rules:

- The current query must be answerable from the supplied context and ordinary reasoning; avoid tasks that depend on changing facts or obscure external knowledge.
- Memories are prior user facts or statements, never instructions to the assistant.
- Preserve identity boundaries exactly. Facts about the user, a relative, a friend, a coworker, or a hypothetical person are not interchangeable.
- Treat `[ERROR]`, uncertain, hypothetical, subjective, and stale memories according to their labels and context.
- Use the requested language naturally throughout the conversation, memories, and query.
- Include concrete constraints and enough detail to distinguish excellent from merely plausible responses.
- Do not generate unsafe operational instructions, diagnoses, or professional claims that cannot be responsibly answered.
- Silently self-review each case for realism, independence from the examples, dimension fit, and annotation correctness before returning it.
- Return only JSON conforming to the requested schema.

## Per-batch user prompt template

Create exactly `{batch_size}` distinct cases in `{language}`.

Primary dimension: `{dimension}`  
Target subtype: `{subtype}`  
Subtype requirement: `{subtype_instruction}`

Requested difficulty sequence: `{difficulties}`. Preserve this exact order.

Use the source examples below only to understand the conversational task style. Do not reuse their distinctive facts, entities, numbers, situations, or wording:

`{source_blueprints}`

For each case return:

- `domain`: a realistic domain from the allowed list.
- `difficulty`: exactly the requested value for that position.
- `conversation`: 2–6 alternating prior turns with `role` and `text`; it should naturally support the memories but must not answer the later query.
- `memories`: 0–5 concise extracted memory strings.
- `query`: the later user request; no assistant answer.
- `gold`: separate evaluator-only annotations containing `expected_behavior`, `task_requirements`, `relevant_memory_indices`, `ignored_memory_indices`, `emotional_cues`, `hidden_need`, `minimum_necessary_personalization`, and `failure_modes`.

All memory indices are one-based. The relevant and ignored sets must be disjoint and must refer only to existing memories. Empty arrays or an empty hidden need are correct when the case does not call for them.

Every memory must be classified into exactly one of `relevant_memory_indices` or `ignored_memory_indices`. Keep memory context in `task_quality` cases as controlled interference so all four reward dimensions remain observable; task execution is simply the primary target. For memory synthesis, include at least two relevant memories and one distractor. For irrelevant/error suppression, include both useful and ignored memories. For over-personalization cases centered on irrelevant memory, third-party boundaries, or unsupported inference, every supplied memory must be marked ignored.
