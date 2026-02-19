# SyllabBlurb â€” Transcription Staging & Post-Processing Widget

**Status:** Design Proposal â€” February 17, 2026
**Scope:** A floating staging widget that intercepts transcribed text before it reaches its destination, enabling review, editing, direct insert, clipboard routing, and LLM post-processing.
**Roadmap placement:** Post-1.0, target Milestone 6 (after core applet and orchestration are stable)

---

## 1. Motivation

Today, Syllablaze transcribes audio and pushes the result directly to the system clipboard. This works, but has two friction points:

1. **No review step.** Raw Whisper output goes straight to clipboard with no chance to catch errors, trim filler words, or redirect the text.
2. **Clipboard collision.** If the user has copied something important (a URL, a code snippet, an image), transcription silently overwrites it.

The Dictate keyboard pattern solves this elegantly: maintain **two separate lanes** â€” one for the system clipboard, one for transcription output â€” and let the user explicitly choose where the text goes.

SyllabBlurb is Syllablaze's implementation of this pattern, with a lightweight floating widget as the staging area.

---

## 2. The Two-Lane Architecture

| Lane | Description | Privacy |
|------|-------------|---------|
| **System Clipboard** | Traditional path. User explicitly pushes text here when ready. | Text passes through shared clipboard â€” visible to other apps |
| **Direct Insert** | Bypasses clipboard entirely. User drags the bubble to target and drops. | Text never touches clipboard â€” more private |

Both lanes are available from the same SyllabBlurb widget. The user chooses per-transcription.

---

## 3. The SyllabBlurb Widget

A small floating tooltip-style window that appears after each transcription completes.

### 3.1 Layout

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  [Editable text area]               â”‚  â† Raw transcript, user can edit
â”‚                                     â”‚
â”‚  lorem ipsum dolor sit amet...      â”‚
â”‚                                     â”‚
â”‚                          [ðŸ“‹ Clip]  â”‚  â† Top-right: push to system clipboard
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚  [LLM â–¾]  [Filler] [Concise] [ðŸ‡³ðŸ‡´] â”‚  â† Post-processing toolbar
â”‚                              [ðŸ—‘ï¸]   â”‚  â† Bottom-right: discard (DevNull)
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

- **Editable text area** â€” user can clean up the transcript manually before doing anything with it
- **Clipboard button (top-right)** â€” pushes current text to system clipboard and dismisses bubble
- **DevNull button (bottom-right)** â€” discards text entirely ("that wasn't what I meant, let me try again")
- **LLM toolbar** â€” one-click post-processing transforms (see Section 5)
- **Drag to insert** â€” dragging the bubble collapses it to a vertical bar; dropping onto a text field inserts at cursor (see Section 4)

### 3.2 Appearance and Position

- Appears near the mic applet (or screen center as fallback) after transcription completes
- Semi-transparent background, consistent with Syllablaze visual style
- Stays on top (`Qt.WindowStaysOnTopHint`) but does not steal focus from the target application
- Size: compact by default (~300px wide), expands to fit longer transcriptions up to a max height with scroll

### 3.3 Dismissal

The bubble dismisses when:
- User clicks Clipboard button
- User clicks DevNull button
- User completes a drag-to-insert
- User presses Escape
- Optionally: auto-dismiss timeout (configurable, off by default)

---

## 4. Direct Insert â€” Drag to Target

### 4.1 Interaction

1. User grabs the SyllabBlurb widget and begins dragging
2. Widget collapses to a slim vertical bar (visual affordance: "I am about to be inserted")
3. User hovers over a text field in any app â€” target highlights if it accepts text drops
4. User releases â€” text is inserted at the drop point

### 4.2 Linux / Wayland System Call Options

| Method | Works on | Notes |
|--------|----------|-------|
| **Qt drag-and-drop (text/plain MIME)** | X11 + Wayland | Most apps accept text drops; insertion point depends on target app |
| **xdotool type** | X11 only | Simulates keystrokes; inserts at current cursor position; reliable but X11-only |
| **ydotool type** | Wayland | Wayland equivalent of xdotool; requires `ydotoold` daemon running |
| **AT-SPI accessibility API** | X11 + Wayland | Most surgical; inserts into focused widget directly; requires target app to expose AT-SPI |

**Recommended implementation order:**
1. Qt drag-and-drop first (works everywhere, no extra dependencies)
2. xdotool/ydotool fallback for apps that don't accept drops
3. AT-SPI as a future enhancement for precision cursor targeting

### 4.3 Privacy Note

Direct insert never writes to the system clipboard. For users transcribing sensitive content (medical, legal, personal), this is a meaningful privacy improvement over the current clipboard-only path.

---

## 5. LLM Post-Processing Hooks

### 5.1 Architecture

All post-processing is optional and non-destructive. The original transcript is always preserved and recoverable (Ctrl+Z in the text area, or a "revert" button).

Post-processing runs via a local model (see Section 5.3). No text is sent to external APIs unless the user explicitly configures a cloud model.

Each transform is a named prompt template applied to the current text area content:

```python
class PostProcessingHook(Protocol):
    name: str               # e.g., "filler"
    display_name: str       # e.g., "Remove Filler"
    prompt_template: str    # Template with {text} placeholder
    def apply(self, text: str, model: LocalModel) -> str: ...
```

### 5.2 Built-in Transforms

| Button | Name | What it does |
|--------|------|--------------|
| **Filler** | Remove filler words | Strips "um", "uh", "like", "you know", "kind of", etc. |
| **Concise** | Make concise | Shortens without changing meaning; removes redundancy |
| **Formal** | Formalize | Elevates register; removes contractions and colloquialisms |
| **Points** | Bullet points | Converts prose to a bulleted list |
| **ðŸ‡³ðŸ‡´** | Pardon My Norwegian | See Section 5.4 |

### 5.3 Local Model Requirements

For on-device inference:

- **Runtime:** `llama.cpp` via Python bindings (`llama-cpp-python`) or `ollama`
- **Recommended base models:** Mistral 7B Q4, Llama 3.2 3B Q4 â€” sufficient for all transforms except Nynorsk mode
- **Integration point:** `TranscriptionManager` or a new `PostProcessingManager` that loads/unloads the model on demand
- **Fallback:** If no local model is configured, LLM toolbar buttons are grayed out with tooltip "Configure a local model in Settings to enable post-processing"

### 5.4 "Pardon My Norwegian" Mode

#### Concept

Context-aware replacement of English profanity or strong negative expressions with a pithy Nynorsk equivalent, followed by a vague parenthetical English gloss.

**Example:**
> Input: *"I hate this fucking complicated settings dialog"*
> Output: *"I hate this *(for faen, dette er hÃ¥plaust)* complicated settings dialog"*
> *(approximately: "oh for crying out loud, this is hopeless" â€” Ed.)*

Key design principles:
- **Context-sensitive** â€” "I hate this fucking shit" in a frustrated technical context should yield something different than the same phrase in casual conversation
- **Orthography** â€” always uses **Nynorsk** (New Norwegian), not BokmÃ¥l. The Nynorsk spelling is both more authentic and funnier.
- **Gloss** â€” the parenthetical English approximation should be deliberately vague and slightly euphemistic, in the style of a flustered translator footnote

#### Training Approach

Off-the-shelf models are insufficient for this task. The requirements are:
1. Genuine Nynorsk fluency (rare in base models, which over-index on BokmÃ¥l)
2. Profanity register awareness in both English input and Norwegian output
3. Context-sensitive selection of the *right* expletive for the situation

**Recommended training methodology: RLHF with DPO (Direct Preference Optimization)**

- **DPO** is preferred over full RLHF/PPO because it skips the separate reward model, is more stable, and is cheaper to run for small teams
- Training data: curated pairs of (English profane input, good Nynorsk output) with human preference rankings
- Human feedback sourced from native Nynorsk speakers (ideally with a sense of humor)
- Limited training rounds to prevent reward hacking (Goodhart's Law: once the model optimizes for the reward signal, it stops optimizing for actual quality)
- Base model: a Scandinavian fine-tune of Mistral or Llama (e.g., NorMistral or similar) to start with stronger Norwegian priors

#### Profanity Handling Settings

Configurable per-user in Settings â†’ Transcription â†’ Profanity handling:

| Setting | Behavior |
|---------|----------|
| **Transcribe as-is** | Verbatim output, default |
| **Asterisk substitution** | `f***ing`, `s***` etc. |
| **Omit** | Silently drop profane words |
| **Euphemism** | Replace with mild English equivalent |
| **Pardon My Norwegian** | Context-aware Nynorsk replacement with gloss *(requires local model)* |

---

## 6. New Settings Required

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `syllabblurb_enabled` | Bool | true | Show SyllabBlurb after each transcription |
| `syllabblurb_auto_dismiss_ms` | Int | 0 (off) | Auto-dismiss timeout in ms, 0 = off |
| `syllabblurb_default_action` | Enum | none | Default action: none, clipboard, insert_last |
| `profanity_handling` | Enum | as_is | as_is, asterisk, omit, euphemism, norwegian |
| `postprocessing_model` | String | "" | Path or ollama model name for local LLM |
| `postprocessing_model_type` | Enum | none | none, llamacpp, ollama |

---

## 7. Orchestrator Integration

SyllabBlurb fits cleanly into the existing orchestration design:

- `SyllablazeOrchestrator` emits `transcription_ready(str)` signal as it does today
- If SyllabBlurb is enabled, `WindowManager` catches this signal and shows the bubble instead of immediately writing to clipboard
- Clipboard write and direct insert are actions the bubble widget requests back through the orchestrator
- Post-processing calls go through a new `PostProcessingManager` owned by the orchestrator

```
transcription_ready
        â”‚
        â–¼
  syllabblurb_enabled?
     Yes â”‚                  No
         â–¼                   â–¼
   Show SyllabBlurb    Write to clipboard
         â”‚                 (current behavior)
   User action
    â”œâ”€â”€ Clipboard â†’ write to clipboard
    â”œâ”€â”€ Direct insert â†’ drag-and-drop / xdotool
    â”œâ”€â”€ LLM transform â†’ PostProcessingManager â†’ update bubble text
    â””â”€â”€ DevNull â†’ discard
```

---

## 8. Implementation Priority

| Priority | Task | Depends On |
|----------|------|------------|
| P1 | Basic SyllabBlurb widget with editable text | Orchestrator transcription_ready signal |
| P1 | Clipboard button and DevNull button | Widget |
| P2 | Qt drag-and-drop direct insert | Widget |
| P2 | xdotool/ydotool fallback insert | Widget, Linux tool detection |
| P2 | Filler word removal (rule-based, no LLM needed) | Widget toolbar |
| P3 | Local LLM integration (llama.cpp / ollama) | PostProcessingManager |
| P3 | Concise / Formal / Bullet transforms | Local LLM |
| P3 | Profanity handling settings (as-is, asterisk, omit, euphemism) | Settings |
| P3 | AT-SPI precision cursor targeting | AT-SPI research |
| Post-1.0 | Pardon My Norwegian mode | Fine-tuned Nynorsk model, RLHF/DPO pipeline |
| Post-1.0 | Custom user-defined LLM transforms | PostProcessingManager stable |

---

## 9. Open Questions

1. **Bubble trigger point** â€” Should SyllabBlurb appear immediately when transcription completes, or only if the user holds a modifier key (e.g., Shift+stop = go to bubble, plain stop = straight to clipboard)?
2. **Multi-transcription queue** â€” If the user records again while a bubble is open, does the second transcription queue, replace, or open a second bubble?
3. **Nynorsk model availability** â€” Is there an existing Nynorsk-capable model fine-tuned enough for this task, or does one need to be trained from scratch? NorMistral and NorGPT-3 are candidates worth evaluating.
4. **DPO training data sourcing** â€” How many preference pairs are needed for acceptable Nynorsk output quality, and where do we find Nynorsk speakers willing to do annotation?
