# Test cases

Each folder is one scenario: `prompt.md` is what the user types, `case.yaml` the expected outcome, `graders/` one pass/fail statement per file, and `files/` (copied in by `place-files.sh`) the inputs. All inputs are fictional.

Run a case by hand: start a fresh session with the skill installed, copy any files from `files/` into the workspace, paste the prompt, and check the reply against each grader. Rerun the cases after every change to the skill.
