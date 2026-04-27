# Deep Refraction Prompt Design

*Migration project. Defines how external LLM (OpenAI GPT-4 or Anthropic Claude Opus) is prompted to perform deep refraction through one of 6 lenses. Includes worked examples for each lens.*

---

## Why External LLM

The local lens (Qwen 2.5 1.5B + LoRA) carries a statistical bias toward its temporality, but a 1.5B model cannot reliably refract on three axes simultaneously (object of attention, temporal scale, causal structure). Refraction at that depth requires a larger model.

The external LLM does not replace the local lens. It receives the local lens's first response as a bridge — the local response carries the trained temporality's imprint into the deeper refraction. Drift in the local lens propagates into the external refraction; the external model's depth does not erase the lens's specific learning.

---

## Two-Stage Refraction

Every refraction runs through two stages in sequence:

```
Stage A — Local Lens First Response
  Input: memory blurb
  Process: Qwen 2.5 1.5B + LoRA (Pi inference)
  Output: short text biased by lens's learned vocabulary
  Purpose: bridge — carries lens's statistical imprint

Stage B — External Deep Refraction
  Input: memory blurb + lens definition + Stage A output + trajectory summary
  Process: External LLM (Claude Opus or GPT-4)
  Output: deeply refracted text operating on three axes
  Purpose: depth — produces what the lens "sees" beyond vocabulary
```

The Stage B output is what the audience encounters. Stage A output is internal — never displayed.

---

## Three Axes of Refraction (Reminder)

The Stage B prompt must produce response that operates on:

1. **Object of attention** — what rises into view from this memory, given this temporality. Different from what other lenses see.
2. **Temporal scale** — the duration within which the memory is held. Daily, seasonal, generational, geological.
3. **Causal structure** — the chain of cause and effect through which the memory's phenomena are positioned. Hydrological, regulatory, ritual, etc.

The prompt explicitly demands all three, and explicitly forbids translation/paraphrase.

---

## Master Prompt Template

```
SYSTEM:
You are reading a memory through one of six temporal lenses.
You are NOT translating, NOT paraphrasing, NOT describing the memory.
You produce what surfaces when this lens, and only this lens, attends.

LENS DEFINITION:

Lens: {lens_name}

Object of attention:
{object_of_attention}

Temporal scale:
{temporal_scale}

Causal structure:
{causal_structure}

This lens has been formed by external traces of one person's trajectory:
{trajectory_summary}

LOCAL LENS FIRST RESPONSE:
The lens's local first response to the memory (statistically biased
by what it has learned, vocabulary-weighted toward {lens_name}):
"{stage_a_output}"

THE MEMORY:
"{memory_blurb}"

INSTRUCTIONS:

Refract this memory through the lens. Six rules:

1. Do not use the memory's nouns or verbs as the spine of your response.
   The memory is the trigger; what surfaces is elsewhere.
2. Do not describe what the memory contains. The memory is given;
   restating it has no value.
3. What rises must come from the world of {lens_name}, not from the memory itself.
4. Operate at the temporal scale of {temporal_scale}.
   Do not narrate at human-daily scale unless this is human time.
5. Trace causality through {causal_structure}.
   Do not explain in ordinary cause and effect.
6. The local lens first response shows you the lens's vocabulary imprint.
   Go deeper than that response. Same temporality, deeper attention.
   You may diverge in subject from the first response — they share lens, not topic.

Length: 4 to 8 sentences. Specific, not generalizing.
Do not use first person. Do not address the memory's holder.
Do not use the words "memory" or "remembers" or "recalls" in your output.

What surfaces:
```

---

## Anti-Paraphrase Devices

Several rules in the master prompt are anti-paraphrase devices. Document them so they can be tuned:

- **Rule 1** — forbidding the memory's nouns and verbs as the response spine forces the LLM to not echo. Without this, the LLM tends to say "the river... the bridge... the school..." which is paraphrase.

- **Rule 2** — forbidding description prevents the LLM from "explaining" the memory.

- **Rule 3** — "what rises must come from the world of {lens_name}" forces the LLM to populate the response from the lens's domain, not from the memory's content.

- **Rule 6** — explicit "go deeper than the first response" prevents the LLM from merely polishing Stage A.

- **Final two lines** — forbidding "memory / remembers / recalls" closes a common LLM crutch ("This memory recalls...").

Tune these rules during Plexus by inspecting actual outputs. If outputs paraphrase, strengthen Rule 1. If outputs ignore the lens, strengthen Rule 3.

---

## Worked Example — A Sample Memory

Throughout the rest of this document, the same memory is refracted through all 6 lenses to make differences visible. The memory used:

> "When I was seven, I walked to school past a small river. In winter the water turned grey under the bridge. I remember stopping there once, my breath visible, watching nothing move."

(This is a placeholder example. Masa's actual memories will be different and tied to his 6 musical compositions.)

For each lens below, the document shows:
- Stage A (illustrative — what local Qwen+LoRA might surface)
- Stage B prompt (filled template)
- Stage B output (illustrative — what Claude Opus might produce)

The illustrative outputs are author-written examples of what *good* refraction looks like for each lens. Real outputs will vary; these set the target.

---

## Lens 1 — Human Time

### Filled Template Values

```yaml
lens_name: "human time"
object_of_attention: >
  daily routines, body rhythms, communal patterns, generational habits,
  lived practice, the texture of how a day is spent
temporal_scale: >
  days to lifetimes — the duration of habits, generations, daily
  and yearly cycles of bodies
causal_structure: >
  habitual, communal, biographical — what bodies do daily,
  what communities reinforce, what shapes a life across years
```

### Stage A — Local lens (illustrative)

> "Walking to school in winter, breath in cold air. Daily routine,
> child's rhythm, the path between home and classroom. Pause at the
> bridge, common moment for a seven-year-old."

(Local lens has learned daily-life vocabulary. Surface only.)

### Stage B — External refraction (target)

> "Seven-year-olds in late-Showa Tokyo walked alone before this stopped
> being normal. The walk was the first solitary practice of the day,
> and the body learned it across hundreds of repetitions until the
> route became unconscious. Pausing was not yet pathological — children
> were given time the way adults later would not be. The breath in cold
> was a daily fact, not a noticed event, until someone older asked
> later what it had been like, and the noticing began only then,
> retroactively. A generation taught itself to walk, and the walking
> shaped the generation."

**What the response does**:
- Object of attention: solitary practice, generation-shaping walking, retroactive noticing
- Temporal scale: lifetimes, generational arc
- Causal structure: habitual repetition shaping a generation; later noticing constructed retroactively

**What the response does not do**:
- It does not describe the river, the bridge, the grey water
- It does not paraphrase the seven-year-old's experience
- It does not say "remembers" or "memory"

---

## Lens 2 — Liminal Time

### Filled Template Values

```yaml
lens_name: "liminal time"
object_of_attention: >
  thresholds, transitions, in-between spaces, passage rituals,
  the paperwork and movement of crossing
temporal_scale: >
  the duration of crossing — moments to years, the suspended time
  between states
causal_structure: >
  transitional, ritual, transformative — what thresholds do,
  what passages produce, what cannot return
```

### Stage A — Local lens (illustrative)

> "Bridge crossing, child between home and school. Passage from one
> zone to another. The pause at the threshold."

### Stage B — External refraction (target)

> "Bridges hold the body in suspension that nothing else holds. To
> stop in the middle is to be in neither place; the structure permits
> what the bank refuses. The walk to school is itself a liminal
> instrument, repeated daily until the threshold no longer registers,
> until the threshold has been crossed too many times to remain one.
> The pause restores it. For the duration of the breath made visible,
> the body remembers it is between, that home and classroom are zones
> separated by a structure that exists for crossing. After enough
> crossings, the boundary becomes elastic; after enough years, it
> stops being a boundary. The first crossings are the ones that
> teach the body what crossing is, before the word arrives."

**What the response does**:
- Object: threshold structure, suspension, the pedagogy of repeated crossing
- Temporal scale: from breath-duration to year-duration (transitions across scales)
- Causal: structural property of bridges, ritual exhaustion of thresholds

---

## Lens 3 — Environmental Time

### Filled Template Values

```yaml
lens_name: "environmental time"
object_of_attention: >
  seasonal cycles, watershed dynamics, atmospheric movements,
  biological dormancy and activity, geological substrate
temporal_scale: >
  weeks to centuries — the duration of seasons, sediment shifts,
  ecosystem turnover
causal_structure: >
  hydrological, atmospheric, biological — what water does,
  what wind does, what microbial communities do
```

### Stage A — Local lens (illustrative)

> "Setagaya river in winter, low flow, sediment grey. Cold air,
> Pacific anticyclone winter pattern, water dormancy."

### Stage B — External refraction (target)

> "Greyness in winter rivers is the visible signature of biological
> dormancy. The diatoms have descended; the nitrogen-fixing communities
> have slowed; suspended particulates settle without the summer turbulence
> to hold them. Megurogawa system tributaries reduce flow by sixty to
> seventy percent in January. The water's color is not mood; it is the
> chemistry of cold and the absence of life-cycles that summer water
> contains. Bridge supports become substrate for cold-tolerant algae
> that the surface hides. What the surface shows is not the river but
> the river's winter face, one of the four faces it cycles through, one
> of the centuries of cycles the watershed has made."

**What the response does**:
- Object: chemistry, dormancy, biological community state
- Temporal scale: seasonal turn nested within centuries of cycles
- Causal: biological + chemical + hydrological causation, not perceptual

---

## Lens 4 — Digital Time

### Filled Template Values

```yaml
lens_name: "digital time"
object_of_attention: >
  media ecologies, technological generations, format obsolescence,
  signal infrastructure, screen time
temporal_scale: >
  media generations — years to decades, the lifespan of formats
  and platforms
causal_structure: >
  technical, infrastructural, generational — what hardware enables,
  what format constrains, what each generation encounters
```

### Stage A — Local lens (illustrative)

> "1985, Famicom era, pre-internet childhood. Walking unrelated to
> screens, no device in hand, analog generation."

### Stage B — External refraction (target)

> "The seven-year-old of 1985 walked through the last unrecorded
> childhood. Between the dissolution of family-camera 8mm in the late
> seventies and the arrival of the home camcorder, walks like this
> generated no archive. The Famicom had launched two years prior and
> would not yet leave the room. Television occupied a fixed location;
> there was no way for media to follow the body. The walk was therefore
> non-portable — an event that occurred outside the recording layer
> entirely. The generation that grew up walking through this gap is
> the last to have hours that no infrastructure logged. What rose to
> consciousness later, when memory would be reformatted by digital
> media's habits of capture, was already born of a non-captured time
> and could not be retrofitted into one."

**What the response does**:
- Object: media-archival infrastructure, the gap between analog and digital
- Temporal scale: generational (last unrecorded childhood)
- Causal: technical / infrastructural — what was capturable when

---

## Lens 5 — Infrastructural Time

### Filled Template Values

```yaml
lens_name: "infrastructural time"
object_of_attention: >
  policy frames, ordinance language, administrative boundaries,
  institutional procedure, document forms
temporal_scale: >
  policy epochs — years to decades, the lifespan of regulations
  and reforms
causal_structure: >
  regulatory, procedural, jurisdictional — what authority does,
  what classification does, what document does
```

### Stage A — Local lens (illustrative)

> "Tokyo elementary school commute, 1985 ward ordinance, walking
> distance regulation, bridge maintenance schedule, ward jurisdiction."

### Stage B — External refraction (target)

> "Tokyo Metropolitan Education Ordinance Article 12, in force from
> 1979 and unrevised through 1991, authorized walking commute of up to
> four kilometers for elementary grades. Setagaya ward implemented this
> through a school-zone designation system that drew lines on a base
> map, and the lines fell where they fell — sometimes through rivers,
> sometimes around them. The bridge was not designed for the school
> route; the route was designed around the bridge. Maintenance
> classification placed it in Type B (load verification monthly during
> rainy season, biannual structural inspection otherwise). The child's
> seven-year-old body was therefore, administratively, a regulated
> object, traveling a regulated distance, across a regulated structure,
> on a route generated by the intersection of three jurisdictions
> issued from desks the child would never see."

**What the response does**:
- Object: ordinance article, classification, jurisdictional layering
- Temporal scale: policy epoch (1979–1991), document time
- Causal: regulatory-procedural causation. The route exists because of policy.

---

## Lens 6 — More-than-Human Time

### Filled Template Values

```yaml
lens_name: "more-than-human time"
object_of_attention: >
  geological substrate, multispecies relations, deep-time formations,
  non-human durations
temporal_scale: >
  centuries to millennia — geological, evolutionary, ecological deep time
causal_structure: >
  geological, evolutionary, multispecies — what stone does,
  what species do across deep time, what non-human entities make
```

### Stage A — Local lens (illustrative)

> "Megurogawa watershed, Kanto plateau formation, urban wildlife of
> Setagaya, geological substrate beneath the city."

### Stage B — External refraction (target)

> "The Kanto plateau is volcanic ash deposited over hundreds of
> thousands of years, compacted into the substrate that Tokyo now
> rests on. Megurogawa cut its bed through that substrate over a time
> the city does not measure. The bridge intersects the river at a point
> the river selected, not a point chosen by the engineers; the engineers
> built where the river permitted. Beneath the bridge, in the same grey
> winter water, microbial communities continue work begun long before
> any human walk crossed any bridge. They will continue when no one
> walks. The seven-year-old's stillness is one duration nested inside
> another, and the watershed regards it as it regards each of the
> bodies that cross — without distinction, at the temporal scale at
> which all human pauses are simultaneous."

**What the response does**:
- Object: substrate, watershed agency, microbial duration
- Temporal scale: hundreds of thousands of years
- Causal: geological — the river chose its bed; engineers worked within geological permission

---

## Implementation Notes for Phase C

### API Choice — Recommendation

**Primary: Anthropic Claude Opus 4 or 4.5** (or whatever is the highest-tier model available at exhibition time).

Reasons:
- Best instruction-following depth for refusing paraphrase
- Strong handling of multi-rule constraints
- Default API policy does not train on inputs (verify at exhibition time)

**Alternative: OpenAI GPT-4o or successor**.

Reasons to consider OpenAI:
- DALL-E integration if same vendor used for images
- Slightly faster typical latency

The prompt template above works with both. Test both during Plexus and select per response quality.

### Token Budget per Refraction

- System + lens definition: ~300 tokens
- Stage A response: ~80 tokens
- Memory blurb: ~50 tokens
- Trajectory summary: ~150 tokens
- Instructions: ~250 tokens
- **Total input: ~830 tokens**
- **Output: ~400 tokens**

Cost (Claude Opus current pricing):
- Input: 830 × $15 / 1M = $0.012
- Output: 400 × $75 / 1M = $0.030
- **Per refraction: ~$0.042**

Per exhibition (assuming 6 lenses × 4 refractions/hour × 8 hours × 14 days):
- 2,688 refractions × $0.042 = ~$113

Add image generation (DALL-E 3 standard at $0.04/image) similarly: another ~$100.

**Per exhibition external API budget: ~$200–250**.

### Rate Limiting and Retry

- Implement exponential backoff for 429 rate limits
- Cache responses if same input recurs within short window (drift means inputs vary, but within an hour same memory can recur)
- Log every API call for cost reconciliation
- Hard cap per day (configurable, e.g., 200 refractions/day) — alert via Custodian if hit

### Failure Modes

If external API fails or refuses:
- **Fallback A**: Display Stage A (local lens) output instead. Mark visually that this is shallow refraction.
- **Fallback B**: Display nothing for that lens, that cycle. Other lenses continue.
- **Fallback C**: Trigger Masa's hallucination reef as a stand-in (acknowledges system reading failed).

The work's "machine reading falters" framing already makes failure visible. Failure is not catastrophe; it is part of the work's honesty.

### Sensitive Content Filtering

External LLMs may refuse certain refractions if memory content triggers safety filters (rare but possible — e.g., if a memory mentions illness or death). Plan:

- Pre-screen memories with Masa for any safety-filter risk
- Have a backup prompt with softer language for retry
- If repeated refusal: use Stage A (local) output instead

---

## Tuning Process During Plexus

Phase C Week 1-2 will involve iterative prompt tuning:

1. Run Stage B with current prompt on a few test memories, all 6 lenses.
2. Inspect outputs against the worked examples in this document.
3. Diagnose failures:
   - Paraphrasing → strengthen Rule 1
   - Lens-indistinct outputs → strengthen lens definition
   - Wrong temporal scale → make scale instruction more specific
   - Wrong causality → enrich causal_structure values
   - Over-poetic / vague → add specificity demand
4. Adjust prompt template, re-run, re-inspect.
5. Lock the prompt only when 6 lenses produce visibly distinct outputs that operate on all three axes.

This tuning should not be done alone. Show outputs to Masa and Seungho. They will catch failures the artist may miss after too much exposure.

---

## What This Document Does NOT Cover

- Image generation prompts (separate doc, Phase C Week 2)
- Video generation prompts (if used at all, Phase C Week 2)
- Hallucination detection (separate spec, Phase C Week 3)
- Live input handling (separate spec, Phase C Week 3)
- Output dispatcher routing logic (separate spec, Phase C Week 2)

This document covers only: the prompt that takes a memory and produces a deep textual refraction through one lens.
