# Concept renders – let the image model imagine

Each concept is shown in two views of the same booth: View 1, chosen from two candidates, and View 2, edited from the chosen View 1. A detail view for the lead concept's materials page is optional. They are what the client remembers, so they must look stunning and premium. The image model is the strongest imagination in this process: give it the idea, the references and the few facts that must hold, and let it design the picture. Do not dictate it.

Make the View 1 images right after the three ideas are chosen (fast start), so the user sees pictures within minutes; the geometry, plan and concept text are developed afterwards from the chosen images. The size block uses the frame's [W] × [D] and the hero height from the idea's rough sizing.

Person-heights are always worked out in metres: a person is 1.75 m (about 5.75 ft), so divide metres by 1.75, or feet by 5.75. When the RFP uses feet, give the platform as [W] ft × [D] ft ([W m] × [D m]); a 10 ft × 10 ft booth is about 1.7 person-heights wide, not 5.7.

## The four rules

1. **Send the references themselves.** Attach the reference image files to every View 1 call (`--ref`): the client's own previous booth, any booth or render the client or the user likes. They carry the client's taste, the structure they recognise, the finish and the polish far better than words. A written description never replaces an attached image, and the references are never turned into a list of things to avoid. In the prompt, say only what to do with them: which part to keep and evolve (a structure, the palette, the glow), and what not to copy (their slogans, posters, other companies' stands). Never attach a massing image or a plan; they are for the appendix only. References shape the picture; they never appear in the proposal, and the proposal never describes them.
2. **Keep the prompt short.** About 200–300 words (the fixed lines of the template are already about 150): the idea, the hero in two or three sentences, the brand colours, the essentials, one line about the references. No camera settings, light recipes, material lists, avoid lists or layout coordinates. A long prompt turns the model into an illustrator of a specification and the picture goes stiff.
3. **Anchor the size in three lines, check the rest afterwards.** The prompt keeps one short size block of three lines (width and depth as person-heights, the whole stand and the hero on one platform with nothing outside it and the open sides, the hero's height as a multiple of a person); without it the model enlarges the stand to fit the idea. Program and details are checked by eye on the result and fixed by editing it (below).
4. **No words, names, years, numbers or logos from the model.** Never ask it to paint the client's name, a slogan, institute or product names, dates, a timeline, figures, screen sizes or the logo. Ask for a plain panel where the logo goes and plain surfaces where text will go. The real logo is composited afterwards (`render.py logo`, with the file named in brief/deck-style.json) or applied by the designer; the copy is set as text in the proposal or in the design drawings. Sizes in the prompt (a 75-inch screen, a 1.8 m counter) match the concept text and geometry.json.

The two View 1 images per concept are two **candidates** to choose from, not a pair. The pair shown to the client is the chosen View 1 and its View 2, edited from it, so both show the same stand.

## View 1 prompt

```
A stunning, high-end exhibition stand design visualization for [client, what they do] at [event].

Idea – "[name]": [the idea and its hero in two or three sentences, as you would tell the client].

Make it look premium and memorable. Brand colours: [names and HEX].
Size – keep it exactly:
- One [W] m × [D] m platform (or [W] ft × [D] ft ([W m] × [D m])), about [W in m / 1.75] person-heights wide and [D in m / 1.75] person-heights deep.
- The whole stand, the hero included, stands on that platform; nothing stands outside it. Open at [sides].
- The tallest element, [the hero], is [H] m, about [H in m / 1.75] times a person.

Essentials: [the program in one line – only what a visitor sees: screen, product displays, counter, seating, interactive; storage only as "a door in the back wall", never as a room]. A plain [colour] panel at [place] where the logo will go. No lettering, numbers or emblems anywhere; screens and product labels are plain. No ceiling, no overhead frame, nothing hung from the hall ceiling. A few visitors for scale, one standing at the front edge.
The attached photos show [what they are]. Keep what makes it theirs – [its signature structure, e.g. the folded light wall], [the palette], [the glow] – and evolve it into this new design, clearly more premium and refined. Do not copy [their slogans, posters, roll-up banners, neighbouring stands].
```

Run it with the references attached, two images per concept:

```
python scripts/render.py hero --prompt concepts/A/prompts/hero.txt --ref input/ref-1.jpg --ref input/ref-2.jpg --out-dir concepts/A/renders --n 2
```

Without references, drop the last line of the prompt. For a concept that starts from somewhere else than the references, the last line keeps only the palette and the glow, or is dropped. Write prompts in English whatever the user's language; give the user a one-line summary in their language.

## Choosing

Make View 1 for all three concepts first, then choose one per concept: the image that looks most premium (at least as good as the client's references) and carries the idea most clearly. Check it by eye; there is no measuring tool:

| Check | How to judge |
| --- | --- |
| Size | With the people as the scale: the front about [W in m / 1.75] person-heights wide, [D in m / 1.75] deep, the hero about [H in m / 1.75] times a person and standing on the platform (in feet, divide by 5.75). Small deviations are fine |
| Open sides | As the frame card gives them |
| Program | Screen, products, counter and seating present |
| Counts | Counted things (leaves, niches, screens) as in the idea |
| Nothing extra | No ceiling, hanging sign, extra room or second level |
| Text | No legible words, names, years, numbers, emblems or logo drawn by the model; the logo panel is plain. A redrawn or wrong logo counts as wrong text |

Record the choice in concept.md: `chosen: renders/hero-v2.png – reason`.

## Fixing

Edit the chosen image with one sentence that names the problem; the design survives:

```
python scripts/render.py fix --base concepts/A/renders/hero-v2.png --add "[correction sentence]" --out-dir concepts/A/renders
```

| Problem | Correction sentence |
| --- | --- |
| Too deep | The stand is only [D] m deep, about [ratio] person-heights from the front edge to the back wall; bring the back wall forward and keep every design element. |
| Hero height | The [hero]'s top is [H] m, about [ratio] times a person; adjust its height only. |
| Extra structure | Remove the [ceiling / hanging sign / side room]; nothing else changes. |
| Wrong count | Show exactly [n] [items]; nothing else changes. |
| Text, numbers, emblems or a logo | Remove the [lettering / numbers / emblems / logo] on [place]; that surface is plain [colour]; nothing else changes. |

`--base` is always a render of this project made by render.py, never a reference file.

Edits change details well but barely change the scale of a whole stand: if the size is clearly wrong (the stand more than about 20 % too wide or deep, or the hero standing outside the platform), take the other candidate or regenerate, with the size block made stronger, instead of fixing. At most three fixes per image; otherwise take the other image or regenerate. If every candidate fails, show the closest and say what is off.

## Blocked renders

A chosen render that still shows wrong text or facts (invented names, wrong years, a redrawn logo, garbled labels) after its fixes, or whose fix could not run (a failed call, no key), is blocked. Write one line in concept.md:

```
blocked: renders/hero-v2.png – invented years on the side panel; fix failed
```

deck.py never places a blocked file, and `deck.py check` reports an error if one is placed. Choose the other candidate or regenerate, then move `chosen:` to the new file. Remove the `blocked:` line only when the file itself has been corrected (a fix makes a new file, so usually it stays).

## View 2

An edit of the chosen View 1, so the design carries across:

```
The same exhibition stand as in this image, same design, materials, colours and light, every element in the same place, seen from the front: from the main aisle, nearly straight on, the whole [W] m width visible with some hall on both sides. A few visitors for scale. No other changes.
```

```
python scripts/render.py front --prompt concepts/A/prompts/front.txt --base concepts/A/renders/hero-v2.png --out-dir concepts/A/renders
python scripts/render.py label concepts/A/renders/hero-v2.png --title "A · [name]" --out concepts/A/A-1-hero.png
python scripts/render.py label concepts/A/renders/front-v1.png --title "A · [name]" --out concepts/A/A-2-front.png
```

Check View 2 the same way as View 1 and record it in concept.md (`front: renders/front-v1.png`). `label` stamps the draft note in Chinese and English when a CJK font is installed, in English only otherwise; the deck uses the unstamped render and stamps it from deck-style.json. Whenever View 1 changes (a fix or a new View 1, for example after a failed geometry check), make View 2 again from it and re-stamp both. Without a usable View 2, the proposal simply has no front page for that concept.

## Detail view (optional)

For the lead concept's materials page: an edit of the chosen View 1 that moves in close on the signature detail, so the page shows material and finish instead of repeating the hero.

```
python scripts/render.py fix --base concepts/A/renders/hero-v2.png --view detail --out-dir concepts/A/renders --add "Move in to an eye-level close-up of [the signature detail]: [materials and light in one phrase]; same design, colours and light; no lettering."
```

It is saved as renders/detail-vN.png. Check it like the others and record it in concept.md (`detail: renders/detail-v1.png – reason`). Without one, the materials page is text only.

## Text and brand

Image models garble text, especially Chinese, and invent names, years, figures and emblems with confidence. So the prompt asks for no text at all and a plain logo panel (rule 4). If a word or number still appears, remove it with a fix; if it stays, block the render. `render.py logo` places the client's real logo file on the plain panel after rendering; otherwise the designer applies the logo and copy. Say so under the images.

## Known habits of image models

- A grid of glowing circles becomes a wall of light bulbs; say what the light passes through.
- Counted things (six leaves, three niches) come out with the wrong count; check and fix.
- Calligraphy and long Chinese text come out as invented characters; ask for plain surfaces instead.
- A logo seen in an attached reference is redrawn, often wrongly; ask for the plain panel and composite the real file.
- Product niches fill up with invented bottles and labels; ask for plain product blocks or empty lit niches.
- A stand drawn too deep is the commonest size error.

## Budget

Per concept: two View 1 candidates, up to three fixes, one View 2 – about six to eighteen paid images for three concepts, plus an optional detail view for the lead. One `hero --n 2` call takes about 2–4 minutes: give it a 10-minute timeout or run it in the background, run the three concepts in parallel, and never start a duplicate call (files are numbered, so a duplicate costs money). Failures and the no-key case: SKILL.md Step 4.

## Without an image tool

Give the prompt pack in work/prompt-pack.md: the View 1 prompt, the references to attach, the View 2 prompt, and the checks above. It is internal and never goes into pack/.
