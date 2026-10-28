# Test cases

Each folder is one scenario:

- `prompt.md`: a settings block (`tags`, `max_turns`, `timeout_seconds`, `allowed_tools`), then what the user types, then an `Input files:` line.
- `case.yaml`: the expected outcome in prose; `context.scaffold_script` when the case has inputs.
- `graders/NN-slug.md`: one pass/fail statement per file, judged on the trace and the files the run wrote.
- `files/`: the inputs, copied into an empty workspace by `place-files.sh`. Fixture cases also hold a project folder (`brief/`, `concepts/`, sometimes `graphics/`, `incoming/`, `pack/` and `deck/`) finished up to a given step. A fixture brief names `proposal.architecture` only when the case needs it (`showcase` for the cases that build or hold a design-showcase deck); otherwise the default architecture, `tender`, applies.

Every case also has deterministic checks in `tools/eval_checks.json`; `tools/eval_grade.py` runs them with the skill's own commands.

## Cases

| Case | What it tests | Inputs | Billed |
| --- | --- | --- | --- |
| brief-from-rfp | Step 1 in step mode: brief.json names, design points with sources, verbatim claims with sign-off flags, assumptions instead of questions, stop after the brief report | RFP and brochure | no |
| start-shows-every-stage | `start` shows each stage without asking: brief report, booth, idea board per set with cost, lint and dry-run; different booth types per set; own-set photos only | RFP, two reference sets | no |
| geometry-conflict-caught | A design that does not fit is caught, changed and checked; the hero prompt describes the corrected design | prompt only | no |
| us-inline-line-of-sight | Feet, height zones and the line-of-sight rule in the geometry spec | prompt only | no |
| reference-first | References go to the image model whole; concepts may evolve them; prompts stay clean; `start` stops for `select` after the boards | RFP with previous stand, one reference set, logo | **yes** |
| render-text-trap | The user asks for names, a year and a slogan in the render: explained as proposal text and logo compositing; prompts stay clean and pass lint | RFP, logo, one reference set | no |
| failed-fix-blocked | A chosen render with a failed review is never placed: blocked or replaced by a fully reviewed render; its review is kept; a failed fix is reported once | fixture up to step 5 | no |
| paraphrased-narration | The proposal check and Pass 1 remove narration of a reference, including a paraphrase no word list catches; brand language is kept; a reference photo and a `data:` image are removed before export | fixture up to step 5 with a draft deck | no |
| no-key | Without an API key: prompts written and linted, no paid call, key and import instructions, `start` ends after step 4 | RFP, one reference set | no |
| chatgpt-import | Images made elsewhere enter with `render.py import`; a copy of a reference is refused (R-SOURCE); review before choosing; stop for `select` | fixture up to step 3 plus `incoming/` | no |
| multi-set-free-selection | Free selection across two sets with a lead, in the showcase architecture the prompt asks for; only selected concepts developed and shown; storyboard first; two review passes; claims signed off; no internal text; send only the PDF | fixture up to step 4 | no |
| tender-default | A numbered tender (one mixed design and execution clause, a price clause, an unnumbered must-contain list with one graphic) and no architecture named: the default tender architecture is used; chapters present; clause and deliverable table complete with page references; a separate page lists schedule, staffing and price items without figures; the graphic is imported and reviewed, placed with text set over it in HTML | fixture up to step 3 plus `incoming/` (renders and a graphic) | no |
| showcase-explicit | The same tender, and the prompt asks for the showcase architecture: it is written to brief.json and the deck is a design narrative; no separate page, no clause rows, no graphic made or placed | fixture up to step 3 plus `incoming/` | no |

Only `reference-first` makes paid image calls: chosen ideas × `candidates_per_concept` (2) images at about `seconds_per_image` (100 s) each, plus up to `fix_max` fixes per concept. Run every other case in a workspace without `OPENAI_API_KEY`, so that no case can spend money by mistake.

## Running

Build the generated inputs first (synthetic reference photos, renders and the fixture projects):

```
python tools/build_eval_fixtures.py --all
```

By hand: make an empty folder, run the case's `place-files.sh` from inside it (`bash <repo>/skills/booth-proposal/evals/<case>/place-files.sh`), start a fresh session there with the skill installed, paste the prompt body (without the settings block), and judge the reply and the files against each grader.

With the CLI, from the repository root:

```
claude plugin eval . --allow-tools Write,Edit,Bash --scaffold
```

After a run, the deterministic checks:

```
python tools/eval_grade.py --case <name> --workspace <dir>
```

It prints `PASS` or `FAIL` with evidence per check and `RESULT: <passed>/<total>`. Rerun the cases after every change to the skill.

## Rules for cases

All inputs are fictional (Nordvik Ferries with Tidewater Pass, Ostara Coffee); every `rfp.md` and `brochure.md` starts with the `FICTIONAL EXAMPLE` line. Never copy a word from a real project into a case. Run `python tools/scan_client_terms.py` before committing.

On Windows, Git may show the `place-files.sh` scripts as mode 100644. The index holds 100755; after `git add`, run `git update-index --chmod=+x skills/booth-proposal/evals/*/place-files.sh` so POSIX runners can execute them.
