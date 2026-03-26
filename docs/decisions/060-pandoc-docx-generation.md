# ADR-060: pandoc + reference-doc 방식 DOCX 생성 표준

- 날짜: 2026-03-16
- 상태: 채택됨
- 결정: 학술 논문/보고서의 DOCX 생성은 pandoc(Markdown → DOCX) + reference-doc(서식 템플릿) 방식을 표준으로 한다. python-docx 직접 코드 생성은 금지. BibTeX + citeproc으로 참고문헌을 자동 처리한다. 항상 PDF도 함께 출력한다(한컴 호환 문제 방지).
- 이유: python-docx로 표/서식을 코드 생성하면 서식이 깨짐(research-project v6 실패). pandoc은 Markdown 원본을 유지하면서 안정적으로 DOCX 변환 가능. libreoffice --headless로 PDF 동시 생성.
- 대안: python-docx (서식 깨짐), LaTeX (한글 설정 복잡), docxtpl (표 복잡 구조 한계)
- 결과: research-project v7~v25 전량 pandoc 생성, pipeline-project 파이프라인 표준
- 출처: 20260316_CC_001_015111_research-project논문재생성_T9OS정비.txt, memory/feedback_always_pdf.md

## Simondon Mapping
기술적 표준의 결정(crystallization): 여러 도구(python-docx, pandoc, LaTeX) 중 pandoc이 환경(한글, 학술지, PDF)과의 호환성에서 최적 구조로 안정화됨.
