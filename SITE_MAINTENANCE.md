# Site maintenance

This repository is the source for https://kwbics.github.io. The former Google Sites address displays this site through a full-page embed. Content changes belong here; nothing needs to be copied into Google Sites. The address bar there remains on Google Sites.

The site consumes al-folio as installed gems. Use local overrides; do not edit the gems.

## Content sources

| Change                | Source                                        | Related files                                                                                                    |
| --------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Home and PI profile   | `_pages/about.md`                             | Keep the PI introduction in `_pages/profiles.md` and `_data/cv.yml` consistent; photo: `assets/img/prof_pic.jpg` |
| Research              | `_pages/projects.md`                          | `_sass/_bics_research.scss`                                                                                      |
| Members and alumni    | `_pages/profiles.md`                          | `assets/img/members/`; photos are shown for current members only                                                 |
| Publications          | `_bibliography/papers.bib`                    | `selected = {true}` also displays a paper on the home page                                                       |
| Teaching              | `_pages/teaching.md`                          |                                                                                                                  |
| Contact               | `_pages/contact.md`                           |                                                                                                                  |
| CV                    | `_data/cv.yml`                                | Single source for the web CV and PDF export                                                                      |
| Email, Scholar, ORCID | `_data/socials.yml`                           |                                                                                                                  |
| Site configuration    | `_config.yml`                                 | Navigation order is in each page's front matter                                                                  |
| Header and logo       | `_includes/header.liquid`, `assets/img/logo/` |                                                                                                                  |
| Shared styles         | `_sass/_bics.scss`                            |                                                                                                                  |

News is disabled. Re-enabling it requires an explicit content decision. Confirm authors, year, venue and DOI against the publisher's record when adding papers. Use the English spelling supplied by each person and the same name for photo alt text. Do not guess biographical dates or publish confidential design, customer or process information.

`exclude:` prevents rendered output, not public repository access. Keep private material out of commits and in `.gitignore`. Routine updates do not modify internal instruction files.

## Common commands

Install the locked dependencies with `bundle install` and `npm ci`. Ruby/Bundler, Node/npm and Python 3 are required; ImageMagick supports image generation. Remote status also requires GitHub CLI (`gh`) with existing repository access. When using the local repository-scoped login, set `GH_CONFIG_DIR="$PWD/.gh"`; do not commit that directory or change global credentials.

| Command                                   | Purpose                                                                                                   |
| ----------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `bin/site check` or `npm run check:site`  | Source and checker tests, formatting, production build and output validation                              |
| `bin/site build`                          | Build the production site into `_site/`                                                                   |
| `bin/site preview --port 4444`            | Serve the built site at http://127.0.0.1:4444                                                             |
| `bin/site status --sha <full-commit-sha>` | Read-only status of workflows for the exact source commit; a separate live render check is still required |

These commands do not stage, commit or push files. Formatting failures identify the files to format; check the diff after applying the locked formatter.

## Update and publish

1. Inspect `git status`, `git diff --cached`, and `git log origin/main..HEAD --oneline`. Preserve unrelated changes and resolve an unexpected staged change before preparing a release.
2. Make the requested content changes in the source files above. Do not edit generated `_site/` output.
3. Inspect `git diff`. Stage only the intended files with `git add <file> ...`, including new files, then review `git diff --cached`. The formatter checks tracked and staged files; it ignores unrelated untracked files.
4. Run `bin/site check`. Inspect affected pages through `bin/site preview` at desktop and mobile widths, including navigation, images and long content. After any corrections, stage the intended files again, rerun `bin/site check`, and inspect the rebuilt pages. Review the final staged diff and commit the verified files.
5. Fetch the target branch and verify that publication is a normal fast-forward. If working on a feature branch, first integrate the reviewed commit into local `main` without overwriting unrelated changes, then run publication and status commands from that main checkout. Verify `HEAD` is the intended commit on `main`; within the authorized publication scope, run `git push origin main`.
6. Check the exact commit with `bin/site status --sha "$(git rev-parse HEAD)"`. For an ongoing run, wait for its completion rather than repeatedly starting new builds. Confirm the affected live pages at https://kwbics.github.io and the Google Sites embed after deployment.

Publication requires exact-SHA status success for Integration tests, Prettier, Deploy site and Visual regression checks, plus Render a CV when applicable, followed by verified live content and Google Sites display. A local build or successful push alone does not. Investigate a failed run before retrying. Never use blanket staging, force-push, or discard unrelated changes to make a release pass.

## CI and CV export

The default integration checks validate this lab site's routes, internal links, assets, publications and build exclusions. The upstream sample-blog tests remain references for theme development, not the consumer site's acceptance criteria. Deployment performs the same core validation before publishing to `gh-pages`.

Responsive checks exercise the actual site at desktop and mobile widths and save screenshots and traces when they fail. Prettier uses the committed lockfile. The CV workflow converts `_data/cv.yml` to pinned RenderCV input and uploads a PDF artifact. It does not rewrite the web CV or make generated-content commits. The existing citation-update schedule is separate and unchanged; this maintenance workflow introduces no new scheduled content updates.
