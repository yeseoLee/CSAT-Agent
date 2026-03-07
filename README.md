# CSAT-Agent

CSAT-Agent는 수능 수학 문제 PDF를 입력으로 받아 텍스트 추출, OCR, 식 정규화, 기호 연산, 검증 단계를 순차적으로 수행하는 `LangGraph` 기반 에이전트 스켈레톤입니다.

현재 저장소는 완성형 서비스가 아니라 파이프라인 구조를 빠르게 실험하고 확장하기 위한 최소 골격에 가깝습니다. 특히 문제 파싱, 풀이 전략 수립, 수식 추출, 자연어 해설은 기본 구현 또는 플레이스홀더 수준입니다.

## 주요 기능

- PDF를 디지털 PDF, 스캔 PDF, 혼합 PDF로 구분
- 디지털 PDF는 텍스트 추출, 스캔 PDF는 OCR 수행
- 페이지별 추출 결과를 병합해 문제 본문 정규화
- SymPy 기반 식 단순화, 미분, 적분, 방정식 풀이 지원
- z3 기반 정수 제약 풀이 함수 포함
- 검증 실패 시 재시도 횟수 안에서 재계획 루프 수행
- Docker 기반 실행 환경 제공

## 처리 흐름

에이전트 그래프는 아래 순서로 동작합니다.

1. 입력 PDF 존재 여부 확인
2. PDF 유형 판별
3. 유형에 따라 텍스트 추출, OCR, 또는 둘 다 수행
4. 수식 스니펫 추출 훅 호출
5. 텍스트와 OCR 결과를 병합해 문제 본문 정규화
6. 문제를 파싱해 연산 종류와 메타데이터 추론
7. 풀이 계획 생성
8. SymPy 또는 z3 도구로 후보 답 계산
9. 답 형식과 범위를 검증
10. 성공 시 응답 생성, 실패 시 재계획 또는 종료

## 프로젝트 구조

```text
src/csat_agent/
  graph/
    builder.py      # LangGraph StateGraph 구성
    nodes.py        # PDF 처리, 파싱, 계획, 풀이, 검증, 설명 노드
    routing.py      # 조건부 분기 로직
    state.py        # AgentState 정의 및 초기 상태 생성
  tools/
    document_tools.py  # PDF 텍스트 추출, OCR, 정규화
    math_tools.py      # SymPy / z3 래퍼
  main.py           # CLI 진입점
```

## 요구 사항

- Python 3.12
- `uv`
- 로컬 OCR 실행 시 Tesseract 설치 필요
- 한국어 OCR까지 사용할 경우 `kor` 언어 데이터 필요

`uv`가 없다면 아래처럼 설치할 수 있습니다.

```bash
python -m pip install uv
```

## 로컬 개발 환경

가상환경과 의존성을 한 번에 준비합니다.

```bash
make sync
```

실행 내용:

- `.venv` 생성: `uv venv .venv --python 3.12`
- 개발 의존성까지 동기화: `uv sync --group dev`

## 실행 방법

기본 실행:

```bash
uv run python -m csat_agent.main "data/problem.pdf"
```

재시도 횟수 지정:

```bash
uv run python -m csat_agent.main "data/problem.pdf" --max-retries 3
```

`make`로 실행할 수도 있습니다.

```bash
make run PDF=data/problem.pdf
```

## Makefile 명령

```bash
make help
```

주요 타깃:

- `make venv`: `.venv` 생성
- `make sync`: 가상환경 생성 후 의존성 설치
- `make lock`: `uv.lock` 갱신
- `make lint`: `ruff check src`
- `make format`: `ruff check --fix src` 후 `ruff format src`
- `make format-check`: 포맷/린트 검증만 수행
- `make run PDF=...`: 로컬에서 에이전트 실행
- `make docker-build`: Docker 이미지 빌드
- `make docker-run PDF=...`: 컨테이너에서 실행
- `make docker-lint`: Docker 내부에서 lint 수행
- `make clean`: `uv` 캐시 정리

## Docker 사용

이미지 빌드:

```bash
make docker-build
```

컨테이너 실행:

```bash
make docker-run PDF=data/problem.pdf
```

Docker 이미지에는 다음이 포함됩니다.

- 베이스 이미지: `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`
- OCR 패키지: `tesseract-ocr`, `tesseract-ocr-kor`
- 실행 명령: `uv run python -m csat_agent.main`

## 현재 구현 한계

- `extract_math_latex()`는 아직 플레이스홀더입니다.
- 문제 파서와 플래너는 규칙 기반 기본 구현만 포함합니다.
- 자연어 해설은 후보 답과 검증 결과를 단순 요약하는 수준입니다.
- 검증 로직은 현재 정수 여부와 값 범위 중심입니다.
- 실제 수능 문제 풀이용으로 쓰려면 LLM 연동, 식 인식, 제약 파서, 검증 전략 고도화가 추가로 필요합니다.

## 권장 확장 방향

- `nodes.py`의 parser/planner/explainer를 LLM Runnable로 교체
- `document_tools.py`에 수식 OCR 또는 Mathpix/pix2tex 연동
- `math_tools.py`의 제약식 파서를 `eval` 기반 스켈레톤에서 안전한 전용 파서로 교체
- 검증 단계에 역대입, 보기 검산, 조건 충족 여부 검사 추가
