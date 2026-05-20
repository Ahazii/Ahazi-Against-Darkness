# Class portraits

Portrait crops extracted from the owned **Four Against Darkness Expanded Edition**
PDF for the character creation screen.

Files are named by class id, for example `warrior.png`, and referenced from
`data/rules/classes.json` as `"image": "classes/warrior.png"`.

To refresh descriptions and art after a rulebook update:

```bash
python tools/extract_class_assets.py
```

The PDF must be present at `Rules/Four_Against_Darkness_Expanded_Edition.pdf`.

These assets ship in the Docker image under `/app/assets/classes/`.
