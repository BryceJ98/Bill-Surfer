# Bill-Surfer Personalities

Each file in this directory defines an AI guide personality. These definitions are used to:
1. Inject a system prompt prefix into AI calls when that personality is active
2. Drive the chat widget persona (name, emoji, intro line, speech style)
3. Define the 8-bit sprite design for future rendering

## Structure of each file

| Section | Purpose |
|---------|---------|
| **Identity** | ID, icon, theme, tier (free / coin cost) |
| **Background** | Character lore — who they are and why they exist |
| **Speech Patterns** | Vocabulary, sentence structure, what to avoid |
| **Abilities & Expertise** | What this personality is particularly good at |
| **Interaction Style** | Example responses for common situations |
| **8-Bit Character Design** | Pixel palette, pose, animation frames for sprite rendering |
| **System Prompt Injection** | The exact text prepended to AI system prompts |

## Active personalities

| File | Name | Cost | Status |
|------|------|------|--------|
| `bodhi.md` | 🏄 Bodhi | Free | Active |
| `bernhard.md` | ⛷️ Bernhard | Free | Active |
| `the_judge.md` | 🃏 The Judge | 75 ⬡ | Active |

## Adding a new personality

1. Create `personalities/<id>.md` following the structure above
2. Add the personality to `PERSONALITIES` in `web/frontend/app/settings/page.tsx`
3. Add its `PersonalityId` type to `web/frontend/lib/ThemeContext.tsx`
4. Add its entry to the `PERSONAS` map in `web/frontend/components/BodhiChat.tsx`
5. Hook the system prompt injection into the backend chat/explain/track routers
