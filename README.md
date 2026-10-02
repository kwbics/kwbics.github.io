# KANGWON BICS

Website of **Bae's Integrated Circuits and Systems Lab (BICS)**, Dept. of Electrical and Electronics Engineering, Kangwon National University.

Live site: <https://kwbics.github.io>

Built with [Jekyll](https://jekyllrb.com/) and the [al-folio](https://github.com/alshedivat/al-folio) starter, hosted on GitHub Pages.

## Local development

```bash
bundle install
bundle exec jekyll serve   # http://localhost:4000
```

## Content

- `_config.yml` — site metadata and feature flags
- `_pages/`, `_news/`, `_bibliography/` — page, news, and publication content
- `assets/` — images and files

## Deployment

Pushing to `main` triggers `.github/workflows/deploy.yml`, which builds the site and publishes it to the `gh-pages` branch.
In the repository settings, set **Pages → Source** to _Deploy from a branch_ → `gh-pages` / `/ (root)`.
