# Homepage — KANGWON BICS 연구실 홈페이지 (kwbics.github.io)

이 리포는 al-folio 테마의 **소비자(consumer)** 다 — 테마 자체를 개발하지 않는다.
상류(al-folio 유지보수자용) 문서는 `UPSTREAM_CLAUDE.md`·`UPSTREAM_AGENTS.md`·`docs/`에 격리 — **이 사이트 작업에 적용하지 않음**.

## 상태

@.project-status.md

(위 파일이 실상태 SSOT — gitignored·비공개. 없으면 새로 만들 것.)

| 스레드 | 상태 | 비고 |
|---|---|---|
| 사이트 운영 (콘텐츠 갱신) | ACTIVE | LIVE: https://kwbics.github.io |
| 후속 4건 (교수 사진·전체 논문·accent 색·구 Google Sites 안내) | PAUSED | `.project-status.md` §Pending |

## 빌드·배포 (검증된 명령)

```bash
export PATH="/opt/homebrew/opt/ruby/bin:$PATH"
bundle exec jekyll build                                   # 로컬 빌드 → _site/
python3 -m http.server 4444 --directory _site              # 미리보기
# 배포: git add -A && git commit && git push origin main → deploy.yml → gh-pages (~2분)
```

## 규칙

1. **공개 리포** — 커밋 메시지·콘텐츠에 AI 도구명 금지 (전역 External Collaboration Protocol).
2. **비공개 파일은 빌드 제외 목록으로 이중 차단** — 하네스 문서(CLAUDE.md·AGENTS.md·UPSTREAM_*)는 `_config.yml` `exclude:`에 등재 유지. 새 내부 문서를 루트에 만들면 exclude에도 추가.
3. git identity는 repo-local로 설정 후 커밋. push는 `GH_CONFIG_DIR="$PWD/.gh"`.
4. 콘텐츠 수정 후 스크린샷 시각 검증(헌법 3조) — 절차는 `.project-status.md` §Local toolchain.
5. 테마 내부(gem) 수정 금지 — 커스터마이즈는 override 파일로. 상류 문서 참조가 필요할 때만 `UPSTREAM_CLAUDE.md`를 읽는다.
6. **세션 시작 = git 상태 1줄 보고** — `git status` + `git log origin/main..HEAD --oneline`로 미배포 커밋을 표면화 (다음 세션이 미배포분을 놓치지 않도록).
7. **배포 완료 판정 = 라이브 렌더 확인** — push 후 https://kwbics.github.io 실제 렌더까지 확인해야 DONE. 로컬 빌드 성공은 READY (state_layers §3).
8. **exclude는 렌더만 차단, 비공개 아님** — `_config.yml` `exclude:`는 사이트 렌더만 막고 repo 소스는 public에 노출. 진짜 민감 파일은 `.gitignore`로.
