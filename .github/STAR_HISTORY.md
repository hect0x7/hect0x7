# Cached Star History

This workflow runs the official `star-history/star-history` backend inside GitHub Actions and publishes repository-owned SVG assets without depending on the public `api.star-history.com` token pool.

## Setup

No additional secret is required. The workflow uses its repository-scoped `GITHUB_TOKEN` to read public repository metadata. Run the `generate animation` workflow once; later runs regenerate the official charts and publish them with the other profile cards.

The workflow pins the upstream project to commit `bcddc9d532b10bac7e0187a741288bf9cab17616`. A small compatibility patch changes the backend's hard-coded token validation repository to `hect0x7/JMComic-Crawler-Python`; chart data sampling and SVG rendering remain upstream code.

## Published assets

```text
https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history-JMComic-Crawler-Python.svg
https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history-JMComic-Crawler-Python-dark.svg
https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history.svg
https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history-dark.svg
```

The repository-specific files contain only `hect0x7/JMComic-Crawler-Python`. The shorter `star-history.svg` names contain the four-repository JMComic ecosystem chart.

Use either light/dark pair in another README:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history-dark.svg">
  <img alt="Star History" src="https://raw.githubusercontent.com/hect0x7/hect0x7/output/profile/star-history.svg">
</picture>
```
