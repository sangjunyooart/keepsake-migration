# Training Guidelines — 6 Lens Agent Formation

*Migration project. For internal reference. Defines what each lens learns, how data is collected, and how training cycles operate.*

---

## Purpose

Each of 6 lens agents is shaped by a distinct temporality through which Masayoshi Ishikawa's life has moved. The lenses must learn the world that surrounded him — never his subjective material. This document defines, for each lens:

- the learning domain (what kinds of texts belong, what does not)
- query templates for active learning
- data sources prioritized
- corpus quality criteria
- training cycle parameters

The purpose of training is NOT to produce knowledge retrieval. It is to form a statistical bias in the lens's weights that makes the lens read inputs through a specific temporality. The trained lens, at inference time, becomes a bridge — its first response carries the temporality's imprint into the deeper refraction performed by external models.

---

## Universal Constraints (Apply to All 6 Lenses)

### Ethical Boundary

**Never collected**:
- Anything authored by Masa (his writings, blog posts, social media, interviews, music criticism by him)
- Anything ABOUT Masa specifically (reviews of his work, biographical pieces)
- His name and known variants in any text — auto-rejected by ethics filter

**The principle**: lenses learn *the world that surrounded him*, not him. If a text describes the place, era, or environmental context he lived in, it qualifies. If a text describes him or contains his words, it is rejected regardless of relevance.

### Quality Criteria

**Accept**:
- Editorial / journalistic prose with substantive content
- Wikipedia, archived journals, government and institutional records
- Memoirs and ethnographies of the period and place (NOT his)
- Scientific and technical reports relevant to the temporality
- Domain-specific reference material

**Reject**:
- Comment threads, forum posts, social media (low signal)
- SEO content, marketing copy, listicles
- Generic encyclopedia entries with no specific era/place anchor
- Translation artifacts (machine-translated stubs)
- Texts shorter than 200 words after cleaning

### Numerical Data

When raw numerical data enters a corpus (NOAA weather records, USGS seismic records, etc.), it must be converted to narrative text via templates before training. Qwen does not learn from JSON. Example template:

```
"On {date}, {station} recorded a maximum temperature of {tmax}°C and 
minimum of {tmin}°C. Precipitation: {prcp}mm."
```

Each adapter (`mac/active_learning/source_adapters/`) handling structured data must include such conversion. Verify when adding new sources.

---

## Lens 1 — Human Time

**Temporality**: daily rhythms of bodies and routines.

### Learning Domain

**Belongs**:
- Daily life records of the cities and neighborhoods he passed through (Setagaya, Bushwick, Williamsburg, Neukölln, Echo Park)
- Generational practice: school-day rhythms of Japanese children in the 1980s, MFA-student daily life in mid-2000s NYC, residency-era schedules in 2010s Berlin
- Memoir literature of his eras, set in his cities, by other authors
- Folk and vernacular records: proverbs, daily idioms, mealtime customs of his eras and places
- Ethnographies of communal life

**Does not belong**:
- Political analysis, abstract sociology
- Policy and law (those go to infrastructural_time)
- Geographic and environmental description (environmental_time)
- Generational media history (digital_time)

### Query Templates

```yaml
human_time:
  - "{location} daily life {period}"
  - "{location} {period} memoir"
  - "{location} {period} household routines"
  - "{location} {period} workplace culture"
  - "{location} schoolchildren {period}"
  - "{location} family customs {period}"
  - "{period} {country} domestic everyday"
```

### Data Sources

Wikipedia (memoir-related entries), Internet Archive (memoirs out of copyright), Project MUSE (open ethnographies), JSTOR Open Access, oral history archives where available.

### Cycle Parameters

- check_interval: 6 hours (medium-frequency cycle, matching the rhythm of daily-life material)
- min_corpus_chunks: 50
- novelty_threshold: 0.4

---

## Lens 2 — Liminal Time

**Temporality**: thresholds, transitions, in-between spaces, passage rituals.

### Learning Domain

**Belongs**:
- Migration narratives of his eras and routes (Japan→US in early 2000s, US→Germany in 2010s, return to US)
- Texts about visa and status transitions of his profile (artist visa, student visa, residency permits)
- Rite-of-passage texts: initiation, threshold, departure, arrival
- Texts about boundary spaces: bridges, airports, train stations, ports, border crossings
- Suspension and waiting (immigration queues, customs, transit lounges)
- Departure and arrival memoir genres

**Does not belong**:
- Travel writing focused on destination experience (too contained)
- Pure political analysis of migration (infrastructural_time)
- Abstract philosophy of liminality without grounded text

### Query Templates

```yaml
liminal_time:
  - "{period} immigrant narrative {country}"
  - "Japanese immigrants United States {period}"
  - "rite of passage {country} {period}"
  - "border crossing {country} {period}"
  - "{location} bridge history"
  - "{location} airport transit experience"
  - "departure arrival narrative {period}"
```

### Data Sources

Migration narrative archives, immigration history journals, ethnographies of border zones, memoir of crossing genre.

### Cycle Parameters

- check_interval: 24 hours (slow cycle, threshold time is patient)
- min_corpus_chunks: 50
- novelty_threshold: 0.5

---

## Lens 3 — Environmental Time

**Temporality**: seasons, weather, watershed, atmospheric and biological cycles.

### Learning Domain

**Belongs**:
- Historical weather data for his cities and periods (Tokyo 1980s-90s, NYC 2000s, Berlin 2010s, LA 2020s)
- Natural disaster records (Hanshin earthquake 1995, Tohoku 2011, Sandy 2012, recent LA fires)
- Local ecology: rivers, watersheds, native species, urban green of his cities
- Seasonal records: phenology, climate normals, atmospheric patterns
- Geological substrate of his places (Kanto plateau, Manhattan schist, Berlin glacial, LA tectonics)

**Does not belong**:
- General climate change discourse without place anchor
- Environmental policy (infrastructural_time)
- More-than-human / multispecies (more_than_human_time, distinct emphasis)

### Query Templates

```yaml
environmental_time:
  - "{location} climate {period}"
  - "{location} weather history {period}"
  - "{location} natural disasters {period}"
  - "{location} watershed hydrology"
  - "{location} ecology {period}"
  - "{location} seasonal patterns"
  - "{location} river systems"
```

### Data Sources

NOAA Climate Data Online, JMA archives (Japan), USGS, EPA records, regional ecological surveys, Wikipedia for natural events. NOAA adapter must use template conversion.

### Cycle Parameters

- check_interval: 12 hours
- min_corpus_chunks: 50
- novelty_threshold: 0.3

---

## Lens 4 — Digital Time

**Temporality**: generational media ecologies, technological transitions, format obsolescence.

### Learning Domain

**Belongs**:
- Media environment of each era and place: 1980s Japan home computing (Famicom, MSX), TV and manga of his childhood, 2000s NYC indie web, 2010s social media, 2020s AI media
- Technical transitions: home computer adoption in Japan, cellphone arrival, broadband, smartphones, streaming
- Format obsolescence: dead platforms, archived UI, sunset products
- Generational media literacy of his cohorts

**Does not belong**:
- General tech industry history without era/place anchor
- Critical theory of digital culture (too abstract)
- Hardware engineering specs (not relevant)

### Query Templates

```yaml
digital_time:
  - "Japan {period} home computing"
  - "{country} {period} media environment"
  - "Famicom Japan childhood"
  - "{country} {period} television culture"
  - "{period} internet adoption {country}"
  - "{period} social media generation"
  - "{period} digital media transition"
```

### Data Sources

Internet Archive (defunct websites), Wikipedia (technology history), retro computing archives, era-specific media studies, technology journalism archives.

### Cycle Parameters

- check_interval: 1 hour (fastest cycle — digital time is rapid)
- min_corpus_chunks: 50
- novelty_threshold: 0.6

---

## Lens 5 — Infrastructural Time

**Temporality**: administrative regimes, institutional procedure, policy and document.

### Learning Domain

**Belongs**:
- Policy and legal text relevant to his cities and eras (immigration, education, urban planning, taxation)
- Administrative document language (ordinance, regulation, statute)
- Institutional procedure: school system structure, visa procedure, residency permit process, university bureaucracy
- Bureaucratic time: waiting periods, processing windows, deadlines, expirations
- Government and institutional records (open access)

**Does not belong**:
- Political opinion or analysis (too narrative)
- Daily-life accounts of dealing with bureaucracy (human_time)
- Liminal narratives of crossing borders (liminal_time, focus on ritual not procedure)

### Query Templates

```yaml
infrastructural_time:
  - "{country} immigration policy {period}"
  - "{country} {period} education ordinance"
  - "{location} {period} urban planning"
  - "{country} {period} taxation reform"
  - "{country} visa procedures {period}"
  - "{country} administrative reform {period}"
  - "Tokyo metropolitan ordinance {period}"
```

### Data Sources

Government open data portals, legal archives (EUR-Lex for Germany, GovInfo for US, e-Gov for Japan), institutional histories, policy think-tank archives, open-access law journals.

### Cycle Parameters

- check_interval: 12 hours
- min_corpus_chunks: 50
- novelty_threshold: 0.35

---

## Lens 6 — More-than-Human Time

**Temporality**: geological substrate, multispecies relations, deep-time formations, non-human durations.

### Learning Domain

**Belongs**:
- Geology of his places (Kanto plateau formation, Manhattan schist, Berlin morainic deposits, LA basin tectonics)
- Multispecies records: urban wildlife of his cities, dominant non-human species, microbial and arthropod communities
- Deep time texts: geological eras of the regions, pre-human history of the land
- Multispecies ethnography (where rigorously documented)
- Tree, river, mountain biographies (texts that treat non-human entities as having time)

**Does not belong**:
- Environmental conservation policy (infrastructural_time)
- Seasonal weather (environmental_time, distinct shorter scale)
- Animal-as-symbol literary criticism (too anthropocentric)

### Query Templates

```yaml
more_than_human_time:
  - "{location} geology"
  - "{location} geological formation"
  - "{location} urban wildlife"
  - "{location} watershed biology"
  - "{location} deep time"
  - "{location} multispecies history"
  - "{location} non-human inhabitants"
```

### Data Sources

USGS, GSI Japan (geological surveys), academic geology open access, multispecies ethnography journals, urban ecology studies, deep time science writing.

### Cycle Parameters

- check_interval: 24 hours (slowest cycle, matching deep time)
- min_corpus_chunks: 50
- novelty_threshold: 0.5

---

## Training Cycle Operation

### When a Cycle Triggers

The meta-controller evaluates each lens periodically (per its `check_interval`). A training cycle triggers when ALL of:

- corpus_count >= min_corpus_chunks
- (now - last_training) >= check_interval
- (new_chunks_since_last_training / corpus_count) >= novelty_threshold

If any condition fails, the lens skips this evaluation and re-checks after one interval.

### What Happens in a Cycle

1. Load base Qwen 2.5 1.5B (frozen)
2. Load latest LoRA adapter for this lens (or initialize new if first cycle)
3. Tokenize processed corpus (1024 tokens per chunk, 64 token overlap)
4. Train 3 epochs:
   - learning_rate: 5e-5
   - per_device_train_batch_size: 2
   - gradient_accumulation_steps: 2
   - gradient_checkpointing: enabled (memory)
   - bf16: enabled (Mac M4 MPS)
5. Save new checkpoint: `mac/adapters/{lens_name}/checkpoint_{timestamp}/`
6. Register with adapter_manager as latest version
7. Trigger push to assigned Pi via rsync over SSH
8. Pi receives, calls `/reload` endpoint, swaps adapter into running model

### Drift Source 1 — Continuous Learning

Each cycle adjusts the LoRA weights slightly based on new corpus. Over weeks, weights drift. The same input rendered before and after a cycle produces different outputs.

### Drift Source 2 — Real-time Data Ingestion

During exhibition, real-time environmental feeds (weather, news of his trajectory cities, gallery sensors) continue to flow into the corpus. New data triggers new training cycles. The lens drifts not only from learned past but from accumulating present.

### Drift Verification

Custodian (helper-side stewarding agent) periodically measures:

- Weight signature of each adapter
- L2 distance between consecutive checkpoints (drift magnitude)
- Cross-lens distance (lens differentiation)

Records appear on dashboard at `/monitor/custodian/`. Sudden spikes or full convergence trigger alerts.

---

## Corpus Hygiene — Periodic Review

The artist (or Custodian, automated) reviews random samples of each lens's corpus weekly during initial training period. Check criteria:

- Does the chunk match the lens's domain (per definitions above)?
- Is the chunk substantive (>200 words, real content)?
- Does it contain Masa keywords? (Should never reach corpus, but verify)
- Is it from a quality source per criteria?

Quarantine bad chunks. Adjust query templates if patterns emerge (e.g., a query consistently retrieves SEO content — narrow it).

---

## When the System Is "Ready"

A lens is considered ready for exhibition when:

- corpus_count >= 500 chunks of accepted material
- training has run >= 20 cycles (sufficient to encode statistical bias)
- weight signature is stable but still drifting (not stuck, not exploding)
- random response sampling shows lens vocabulary distinct from base Qwen
- random response sampling shows distinct vocabulary from other 5 lenses

This typically requires 4-6 weeks of continuous training after Masa's timeline arrives. Active learning + historical collector populate the corpora; meta-controller schedules training; system runs autonomously.

---

## What Training Does NOT Do

To avoid misunderstanding:

- It does not memorize specific facts. It biases statistical prediction.
- It does not produce knowledge retrieval. The lens cannot be queried for facts.
- It does not encode interpretive judgment. The lens has no opinions.
- It does not model Masa. The lens models the temporality of the world surrounding him.

Training produces a small, distributed, statistical imprint — 4.4M parameters of subtle bias on top of the frozen 1.5B base. That imprint is the lens's "having lived" the temporality. It is not knowledge; it is shape.
