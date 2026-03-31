# Anki Context Shuffler

An Anki addon that intercepts card rendering during review sessions and replaces example sentences with LLM-generated variations. When you review a flashcard containing a target word and an example sentence, the addon calls a local LLM to generate a new sentence using the same target word but in a different situation, helping you encounter vocabulary in varied contexts for better retention.

## Key Features

- **Contextual Variation**: Automatically generates new example sentences using the same target word
- **SQLite Caching**: Caches generated variations per card to avoid redundant API calls
- **Deck Filtering**: Apply the addon to specific decks or all decks
- **Non-Blocking**: LLM calls run in background threads so the UI never freezes

## Tech Stack

- **Runtime**: Python 3.x (bundled with Anki)
- **GUI Framework**: PyQt5/PyQt6 (via Anki's `aqt` module)
- **Database**: SQLite 3 (Python stdlib `sqlite3`)
- **HTTP Client**: `urllib.request` (Python stdlib)

## Prerequisites

- **Anki** (latest version recommended)
- A local LLM server running one of:
  - [Ollama](https://ollama.com/) (default: `http://localhost:11434`)
  - [llama.cpp](https://github.com/ggerganov/llama.cpp) server (default: `http://localhost:8080`)
  - [vLLM](https://github.com/vllm-project/vllm) (default: `http://localhost:8000`)
  - [LM Studio](https://lmstudio.ai/) (default: `http://localhost:1234`)
- A model loaded in your chosen LLM server (e.g., `qwen3.5:4b`)

## Installation

### 1. Locate Your Anki Addons Directory

| OS | Path |
|---|---|
| **Windows** | `%APPDATA%\Anki2\addons21\` |
| **macOS** | `~/Library/Application Support/Anki2/addons21/` |
| **Linux** | `~/.local/share/Anki2/addons21/` |

You can also find it from within Anki: **Tools → Add-ons → Open Add-ons Folder**

### 2. Install the Addon

Copy the entire `Anki Context Shuffler` folder into the `addons21` directory.

### 3. Restart Anki

Close and reopen Anki for the addon to load.

## Configuration

Open the settings dialog from **Tools → Anki Context Shuffler Settings...**

### Settings Overview

| Setting | Default | Description |
|---|---|---|
| **Enabled** | `true` | Master on/off toggle for the addon |
| **Target Word Field** | `TargetWord` | Name of the note field containing the word to reuse in generated sentences |
| **Context Sentence Field** | `ExampleSentence` | Name of the note field containing the original example sentence to replace |
| **Ollama API URL** | `http://localhost:11434/api/generate` | URL of your LLM server's API endpoint |
| **Model** | `qwen3.5:4b` | Model name to use for generation (auto-populated from provider) |
| **Temperature** | `0.7` | Generation temperature (0.0 = deterministic, 1.0 = creative) |
| **System Prompt** | *(see below)* | Instructions given to the LLM for generating sentences |
| **Enabled Decks** | `Default` | Deck whitelist — one deck name per line. Leave empty to apply to all decks |

### Default System Prompt

The default system prompt instructs the LLM to:

1. Generate a single sentence using the target word
2. Use a different context than the original sentence
3. Keep the sentence natural and appropriate for language learning
4. Return only the sentence with no additional text

### Field Mapping

Your Anki note type must have fields that match the configured **Target Word Field** and **Context Sentence Field** names. By default:

- **TargetWord**: The vocabulary word you want to see in new contexts
- **ExampleSentence**: The original example sentence that will be replaced

If your note type uses different field names, update them in the settings dialog.

## Usage

### Basic Workflow

1. **Start your LLM server** (e.g., `ollama serve` or `llama-server`)
2. **Open Anki** and start a review session on an enabled deck
3. **Review cards normally** — the addon automatically:
   - Detects cards with a target word and example sentence
   - Calls the LLM to generate a new sentence (first time only per card)
   - Replaces the original sentence on the card with the generated variation
   - Caches the result so the front and back of the card match

### Session Behavior

- **First review of a card**: The addon checks the cache. If no cached variation exists, it triggers background generation. The original sentence is shown while generation happens in the background.
- **Subsequent views of the same card** (e.g., showing the back): The cached or session-stored variation is used instantly, and then a new one is generated and cached after the card review.
- **Next review of the same card**: The newly cached variation is reused.

### Deck Filtering

By default, the addon only applies to the "Default" deck. To enable it for other decks:

1. Open **Tools → Anki Context Shuffler Settings...**
2. In the **Enabled Decks** field, enter deck names (one per line)
3. Leave the field empty to apply to all decks

Example:
```
Default
Japanese::Vocabulary
Spanish::Verbs
```

### Cache Management

Generated variations are stored in `cache.db` (SQLite) in the addon's directory. To clear all cached variations:

1. Open **Tools → Anki Context Shuffler Settings...**
2. Click **Purge Cache**

This is useful if you want to regenerate all sentences with a new model or updated system prompt.

## Troubleshooting

### LLM Connection Fails

**Symptom**: No variations are generated, or you see a connection error tooltip.

**Solutions**:
1. Verify your LLM server is running (`curl http://localhost:11434/api/tags` by default for Ollama)
2. Check the API URL in settings matches your server
3. Ensure the model name is correct and the model is loaded
4. Use the **Test Connection** button in the settings dialog

### Original Sentence Not Replaced

**Symptom**: Cards show the original example sentence instead of a generated one.

**Solutions**:
1. Check that the **Enabled** checkbox is checked
2. Verify the deck is listed in **Enabled Decks** (or the field is empty for all decks)
3. Confirm your note type has fields matching **Target Word Field** and **Context Sentence Field**
4. Check that both fields contain content on the card

### Generated Sentences Are Poor Quality

**Symptom**: Generated sentences are nonsensical, too long, or don't use the target word.

**Solutions**:
1. Lower the **Temperature** (try 0.3-0.5 for more consistent output)
2. Edit the **System Prompt** to be more specific about your requirements
3. Try a different or larger model
4. Ensure the target word field contains a single word, not a phrase

### Cache Issues

**Symptom**: Old variations persist after changing models or prompts.

**Solution**: Open settings and click **Purge Cache** to clear all cached variations.

## Why Local LLMs?

- **Privacy**: Your vocabulary data never leaves your machine
- **Speed**: No network latency to external APIs
- **Cost**: No per-request fees
- **Offline**: Works without internet once the model is downloaded

## License

This project is provided as-is for personal use.
