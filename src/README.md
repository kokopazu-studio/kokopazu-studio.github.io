# kokopazu.com — 소스 (src/)

정적 사이트 빌드 소스입니다. GitHub Pages는 저장소 루트(빌드 산출물)를 그대로 서빙합니다.

## 빌드

```bash
python src/build.py          # 전체 빌드: 이미지(webp/jpg)·영상 복사·로고·프레스킷 zip·페이지
python src/build.py --pages  # 페이지만 재생성 (문구/템플릿 수정 시, 빠름)
```

필요 패키지: `jinja2`, `Pillow`, `markupsafe` (Jinja2에 포함).

## 구조

| 경로 | 역할 |
|---|---|
| `facts.json` | **단일 원본** — 출시일/상태, 가격, 플랫폼, 언어, 링크, UTM, 트레일러 ID, SEO 문구. 날짜·가격·링크는 여기서만 수정 |
| `content/ko.json`, `content/en.json` | 페이지 문구 (카피 덱과 동일) |
| `media.json` | 이미지/영상/로고/프레스킷 원본 경로와 처리 규칙 (원본은 읽기만 함) |
| `templates/` | `base.html`(공통), `index.html`(메인 KO/EN), `presskit.html`, `redirect.html`, `404.html` |
| `static/css/site.css`, `static/js/site.js` | 그대로 `assets/css`, `assets/js`로 복사 |

## 출시 당일 전환

`facts.json` → `"release": {"state": "released", ...}` 로 바꾸고 `python src/build.py --pages` → 히어로 칩·CTA·출시 정보·순위표 버튼·프레스킷 문구가 "출시됨/구매"로 전환됩니다.

## 트레일러 등록

`facts.json` → `"trailer": {"youtube_id": "XXXXXXXXXXX"}` → 빌드하면 트레일러 섹션이 나타납니다(lite embed, youtube-nocookie).

## 규칙

- 이메일은 `kokopazustudio@gmail.com` 만 사용. `contact@kokopazu.com` 금지.
- 게임 규모 숫자(챕터/스테이지/보스/몬스터/플레이 시간)는 쓰지 않는다.
- 정식 도메인은 `https://kokopazu.com` (www 아님).
