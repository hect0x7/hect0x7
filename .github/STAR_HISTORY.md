# Cached Star History

This workflow runs the official `star-history/star-history` backend inside GitHub Actions and publishes repository-owned SVG assets without depending on the public `api.star-history.com` token pool.

## Setup

1. Create a fine-grained GitHub token that can read metadata for every repository in `.github/star-history-repositories.json`.
2. Add it to this repository as an Actions secret named `STAR_HISTORY_TOKEN`.
3. Run the `generate animation` workflow once. Later runs regenerate the official chart and publish it with the other profile cards.

The workflow pins the upstream project to commit `bcddc9d532b10bac7e0187a741288bf9cab17616`. A small compatibility patch changes the backend's hard-coded token validation repository to the first configured repository; chart data sampling and SVG rendering remain upstream code.

## Published assets

```text
https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history.svg
https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history-dark.svg
```

Use both themes in another README:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history-dark.svg">
  <img alt="Star History" src="https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history.svg">
</picture>
```
