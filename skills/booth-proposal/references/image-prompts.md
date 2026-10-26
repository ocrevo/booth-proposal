# Concept renders – let the image model imagine

Each concept is shown in two views of the same booth: View 1, chosen from two candidates, and View 2, edited from the chosen View 1. They are what the client remembers, so they must look stunning and premium. The image model is the strongest imagination in this process: give it the idea, the references and the few facts that must hold, and let it design the picture. Do not dictate it.

Make the View 1 images right after the three ideas are chosen (fast start), so the user sees pictures within minutes; the geometry, plan and concept text are developed afterwards from the chosen images. The size block uses the frame's [W] × [D] and the hero height from the idea's rough sizing.

Person-heights are always worked out in metres: a person is 1.75 m (about 5.75 ft), so divide metres by 1.75, or feet by 5.75. When the RFP uses feet, give the platform as [W] ft × [D] ft ([W m] × [D m]); a 10 ft × 10 ft booth is about 1.7 person-heights wide, not 5.7.

## The three rules

1. **Send the references themselves.** Attach the reference image files to every View 1 call (`--ref`): the client's own previous booth, any booth or render the client or the user likes. They carry the client's taste, the structure they recognise, the finish and the polish far better than words. A written description never replaces an attached image, and the references are never turned into a list of things to avoid. In the prompt, say only what to do with them: which part to keep and evolve (the portal, the wall), and what not to copy (their slogans, posters, other companies' stands). Never attach a massing image or a plan; they are for the appendix only.
2. **Keep the prompt short.** About 150–250 words: the idea, the hero in two or three sentences, the brand colours, the essentials, one line about the references. No camera settings, light recipes, material lists, avoid lists or layout coordinates. A long prompt turns the model into an illustrator of a specification and the picture goes stiff.
3. **Anchor the size in three lines, check the rest afterwards.** The prompt keeps one short size block of three lines (width and depth as person-heights, the whole stand and the hero on one platform with nothing outside it and the open sides, the hero's height as a multiple of a person); without it the model enlarges the stand to fit the idea. Program and details are checked by eye on the result and fixed by editing it (below).

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

Essentials: [the program in one line: screen, product displays, counter, seating, interactive]. The letters "[NAME]" once; no other text. No ceiling, no overhead frame, nothing hung from the hall ceiling. A few visitors for scale, one standing at the front edge.
The attached photos show [what they are]. Keep what makes it theirs – [its signature structure, e.g. the rounded portal arch], [the palette], [the glow], [the logo] – and evolve it into this new design, clearly more premium and refined. Do not copy [their slogans, posters, roll-up banners, neighbouring stands].
```

Run it with the references attached, two images per concept:

```
python scripts/render.py hero --prompt concepts/A/prompts/hero.txt --ref input/ref-1.jpg --ref input/ref-2.jpg --out-dir concepts/A/renders --n 2
```

Without references, drop the last line of the prompt. Write prompts in English whatever the user's language; give the user a one-line summary in their language.

## Choosing

Make View 1 for all three concepts first, then choose one per concept: the image that looks most premium (at least as good as the client's references) and carries the idea most clearly. Check it by eye; there is no measuring tool:

| Check | How to judge |
| --- | --- |
| Size | With the people as the scale: the front about [W in m / 1.75] person-heights wide, [D in m / 1.75] deep, the hero about [H in m / 1.75] times a person and standing on the platform (in feet, divide by 5.75). Small deviations are fine |
| Open sides | As the frame card gives them |
| Program | Screen, products, counter and seating present |
| Counts | Counted things (leaves, niches, screens) as in the idea |
| Nothing extra | No ceiling, hanging sign, extra room or second level |
| Text | Only the client's name is legible; no invented words, dates or garbled characters |

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
| Wrong count or names | Show exactly [n] [items]; [names]; nothing else changes. |
| Garbled or invented text | Remove the [text] at [place]; that surface is plain; nothing else changes. |

Edits change details well but barely change the scale of a whole stand: if the size is clearly wrong (the stand more than about 20 % too wide or deep, or the hero standing outside the platform), take the other candidate or regenerate, with the size block made stronger, instead of fixing. At most three fixes per image; otherwise take the other image or regenerate. If every candidate fails, show the closest and say what is off.

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

Check View 2 the same way as View 1. `label` stamps the draft note in Chinese and English when a CJK font is installed, in English only otherwise. Whenever View 1 changes (a fix or a new View 1, for example after a failed geometry check), make View 2 again from it and re-stamp both.

## Text and brand

Image models garble text, especially Chinese. Keep legible text to the client's Latin-letter name; where the idea needs other words, check them and fix or remove what is wrong. If the client supplied a logo file, `render.py logo` places it after rendering. The designer applies the real logo and copy; say so under the images.

## Known habits of image models

- A grid of glowing circles becomes a wall of light bulbs; say what the light passes through.
- Counted things (six leaves, three niches) come out with the wrong count; check and fix.
- Calligraphy and long Chinese text come out as invented characters; ask for plain surfaces instead.
- A stand drawn too deep is the commonest size error.

## Budget

Per concept: two View 1 candidates, up to three fixes, one View 2; each image takes one to two minutes.

## Without an image tool

Give the prompt pack: the View 1 prompt, the references to attach, the View 2 prompt, and the checks above.
