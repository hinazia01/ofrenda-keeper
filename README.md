# Ofrenda Keeper 🕯️

A local remembrance keeper for Día de los Muertos — built for the
Hacktoberfest 2026 DEV Challenge, Week 4: *Ghost in the Machine*.

You write memories of loved ones as simple `.txt` files. One command
weaves them into a beautiful, self-contained remembrance page
(`out/ofrenda.html`) — candle glow, marigolds, their names, and the words
you kept for them.

**Everything happens on your machine.** No cloud, no account, no API.
Family stories are the most private data there is; this tool treats them
that way.

## How it works

- **Rules do the structure** — parsing memory files (`Name:`, `Dates:`,
  `Place:`, `Memory:`), HTML-escaping every word you wrote (so a `<`
  in a memory can never break the page), and building the page.
- **Gemma** (Google's open-weight model, running locally through
  [Ollama](https://ollama.com)) does only the writing: a warm 2–3
  sentence tribute per person.
- **No Ollama?** A template fallback writes the tribute instead — and
  every tribute is labelled with the engine that wrote it
  (`gemma-local` or `fallback-rules`). Nothing is faked.
- A **prompt-echo guard** rejects model replies that echo the prompt's
  instructions instead of writing a real tribute, and falls back honestly.

## Run it

```powershell
ollama pull gemma3:1b
python make_sample_memories.py     # fictional samples to try it
python ofrenda.py memories
# open out/ofrenda.html in your browser
```

Write your own memories as `.txt` files in `memories/`:

```
Name: Dada Ji
Dates: 1940 - 2019
Place: Bahawalpur
Memory: He read the newspaper aloud every sunrise...
```

The `memories/` folder is gitignored — your real stories are never
pushed anywhere.

## Tests

13 automated tests (standard library, no Ollama needed):

```bash
python -m unittest discover -s tests -v
```

Covering: memory-file parsing, the prompt-echo guard, HTML escaping of
user content, the self-contained page (no external requests), and a full
end-to-end run with a stubbed model.

## Why open, why local

A remembrance is intimate: names, dates, family stories. A cloud service
could do this — but then your family's memories would sit on someone
else's server, inside a product that might disappear one day. Ofrenda
Keeper runs on an open-weight model you own, on a machine you own, with
code you can read. Set it up once; it works with the internet off, and
it costs nothing, forever.

## License

MIT — see LICENSE.
