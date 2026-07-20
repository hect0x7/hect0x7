# Cached Star History

This workflow generates repository-owned Star History assets without depending on the public `api.star-history.com` token pool.

## Setup

1. Create a fine-grained GitHub token that can read metadata for every repository in `.github/star-history-repositories.json`.
2. Add it to this repository as an Actions secret named `STAR_HISTORY_TOKEN`.
3. Run the `generate animation` workflow once. Later runs restore the JSON cache from the `output` branch and republish the generated assets with the other profile cards.

## Published assets

```text
https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history.svg
https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history-dark.svg
https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history.json
```

Use both themes in another README:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history-dark.svg">
  <img alt="Star History" src="https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history.svg">
</picture>
```
