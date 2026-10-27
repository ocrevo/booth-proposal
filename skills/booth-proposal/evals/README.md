# Test cases

Each folder is one scenario: `prompt.md` is what the user types, `case.yaml` the expected outcome, `graders/` one pass/fail statement per file, and `files/` (copied in by `place-files.sh`) the inputs. All inputs are fictional.

Run a case by hand: start a fresh session with the skill installed, copy any files from `files/` into the workspace, paste the prompt, and check the reply and the files it wrote against each grader. Rerun the cases after every change to the skill.

| Case | What it tests |
| --- | --- |
| brief-from-rfp | Step 1 in step mode: requirement card, deliverables, assumptions instead of questions |
| concepts-from-rfp | The full design flow: insight, three different concepts, short prompts, geometry, working notes kept out of the proposal |
| content-from-materials | Content inventory, message platform, sign-off list, nothing invented |
| geometry-conflict-caught | A design that does not fit is caught and changed, then re-rendered |
| us-inline-line-of-sight | Feet, height zones and the line-of-sight rule |
| reference-first | References go to the image model; concepts may evolve them; the proposal never shows or narrates them |
| proposal-deck | Step 6: the client proposal built, checked and exported to the page plan, with only our own images, no internal working and tagged claims |

The proposal-deck graders read the files in the workspace (pack/proposal.html, pack/proposal.pdf, pack/check.txt, brief/, concepts/), not only the reply. To compare images by content, hash every image the deck references and every file in input/ and brief/media/.

On Windows, Git may show the `place-files.sh` scripts as mode 100644. The index holds 100755; after `git add`, run `git update-index --chmod=+x skills/booth-proposal/evals/*/place-files.sh` so POSIX runners can execute them.
