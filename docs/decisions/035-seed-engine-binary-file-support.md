# ADR-035: T9 Seed 엔진 바이너리 파일 파싱 확장

- 날짜: 2026-03-16
- 상태: 채택됨
- 결정: t9_seed.py의 reindex 대상을 MD 파일에서 docx, pdf, xlsx, txt, csv, log, 이미지, 동영상으로 확장한다. parse_file() 함수로 python-docx/pymupdf/openpyxl 기반 내용 파싱을 수행하고, FTS5에 전문 인덱싱(body_preview 500자 → full_body 전문)을 적용한다.
- 이유: Downloads에서 T9OS로 이관된 research-project 파일(docx, xlsx)이 검색 불가. "정규직비율" 같은 키워드로 docx 내용을 찾을 수 있어야 T9 Seed가 진정한 단일 진입점이 됨.
- 대안: 외부 검색 도구 사용 (Buy 원칙에 부합하나 FTS와 통합 불가), MD 변환 후 인덱싱 (변환 품질 문제)
- 결과: 25건 → 148건 → 343건 인덱싱, transition()에서 바이너리 파일 보호, relate()에서 비-MD 파일 보호
- 출처: 20260316_CC_001_015111_research-project논문재생성_T9OS정비.txt

## Simondon Mapping
전개체적 장(preindividual field)의 확장: 검색 가능한 잠재성의 풀이 MD 파일에서 모든 디지털 산출물로 확대되어 개체화의 원천이 풍부해짐.
