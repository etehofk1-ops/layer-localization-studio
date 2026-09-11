# v0.1 검증 기록

2026-09-11의 0.1.1 보안 수정·회귀 검증은 [공개 전 점검 기록](security-review-2026-09-11.md)에 추가했습니다. 아래는 0.1.0 당시의 기록을 보존한 것입니다.

실행일: 2026-09-07. Windows, Python 3.11.9, Pillow 12.3.0, psd-tools 1.18.0.

선택 경로와 실제 실행 경로는 Codex 직접 구현 및 자체 검증입니다. 외부 에이전트 교차 검토는 실행하지 않았습니다. 원래 게임 프로젝트를 수정하지 않고 독립 디렉터리와 새 가상환경에서 검사했습니다.

| 검사 | 결과 | 근거 |
| --- | --- | --- |
| 새 venv에서 `pip install -e .` | PASS | 빌드 및 런타임 의존성 설치 완료 |
| `pip check` | PASS | No broken requirements found |
| `python -m unittest discover -s tests -v` | PASS | 13/13 tests |
| Python compileall | PASS | src, examples, tests 구문 검사 |
| Codex skill-creator quick_validate | PASS | UTF-8 모드로 스킬 형식 검사 |
| 합성 fixture demo + CLI verify | PASS | 24개 파일 SHA-256 및 3-layer PSD 검사 |
| 한글 이름·순서·opacity·visibility | PASS | PSD 재열기, 숨긴 레이어 포함 |
| 개별 PSD 레이어 픽셀·알파 | PASS | 보관된 레이어 PNG와 비교 |
| 밝고 어두운 바탕의 PNG/PSD 합성 | PASS | 채널 최대 차이 1, 평균 약 0.27144 |
| 합성 알파 | PASS | 최대 차이 0 |
| ZIP 생성 | 없음 | 폴더 단위 보관 |

13개 테스트는 원본 바이트 보존, 픽셀 알파를 고려한 색 측정, 사전 분석 요구, 실패 시도 보관과 선택 차단, 생성 원본 변조, 레이어 변조, 같은 ID/revision 덮어쓰기 차단, 잘못된 캔버스/합성 모드 차단, 원본의 생성물 등록 차단, 경로 이탈 차단, CLI 실패 코드, 처리 코드의 보관과 비실행, 이전 revision 재검증을 포함합니다.

테스트 도형은 직접 만든 fixture이며 실제 이미지 생성 호출은 0회입니다. 해당 예제에서 검토 완료 값은 합성 fixture 설정에 따른 것이며 사람의 게임 아트 검수를 의미하지 않습니다.

실행하지 않은 범위: 실제 게임 이미지 현지화, 새로운 이미지 생성, Photoshop GUI 열기, macOS/Linux 실행, 실제 게임 적용, 원본 충실도·글씨 가독성 최종 검수, 외부 고객 전달/배포. 구조 검증은 이 범위의 완료나 승인을 대신하지 않습니다.

Windows에서 스킬 검사기의 기본 텍스트 인코딩이 cp949라 UTF-8 문서를 읽지 못해 `python -X utf8`로 검사했습니다. 검사기에 필요한 PyYAML은 로컬 개발 가상환경에만 설치했으며 프로젝트 런타임 의존성은 아닙니다.
