# User Icon Assets

Put individually downloaded icon files in this folder. The Icon Editor lists
these files automatically and stores their paths as:

```text
icons/user/example.svg
```

Deployment model:

1. Add files to `assets/icons/user/` in the project.
2. Commit and push them with the app.
3. Rebuild/redeploy the Docker container.
4. The image copies them to `/app/assets/icons/user/`.
5. Use `/static/icon-editor.html` to assign files and attribution metadata.

For Noun Project free downloads, keep the icon black-only and fill in the
source URL, artist attribution, license, and description in the Icon Editor.
The editor can derive the source URL from filenames like
`noun-monster-8297012.svg`, but it cannot know the artist name.

The `game-icons/` subfolder contains curated SVG assets imported from
https://game-icons.net and assigned through `data/rules/icons.json`. Keep them
monochrome black on a transparent background; app CSS recolors them in map
markers and class badges.
