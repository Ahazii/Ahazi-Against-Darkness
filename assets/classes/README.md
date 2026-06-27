# Class portraits

Portrait crops for the character creation screen.

## Expanded Edition (20 classes)

Extracted from `Rules/Four_Against_Darkness_Expanded_Edition.pdf` via:

```bash
python tools/extract_class_assets.py
```

## TCOTFD and Netherworld (6 classes)

Extracted from owned supplements via:

```bash
python tools/extract_tcotfd_class_assets.py
```

| Class | Source |
| --- | --- |
| Wandering Alchemist, Satyr, Conservationist | `Rules/The_Courtship_of_Flower_Demons.pdf` |
| Demonologist, Cambion, Succubus | `Rules/Four Against_the_Netherworld.pdf` (Cambion/Succubus cropped from p.13 collage) |

Files are named by class id, for example `warrior.png`, and referenced from
`data/rules/classes.json` as `"image": "classes/warrior.png"`.

These assets ship in the Docker image under `/app/assets/classes/`.
