# Layer Localization Studio

게임 UI 이미지의 **원본 분석 → 레이어 생성 → 현지화 → PNG·PSD 조립 → 보관·검수**를 재사용할 수 있게 정리한 제작 도구와 에이전트 스킬입니다.

후루요니 한글패치에서 발전시킨 제작 방식을 게임에 종속되지 않는 형태로 옮겼습니다. 현재는 오픈소스 공개를 준비하는 **비공개 저장소**입니다. 랜딩페이지나 패치 배포 서버가 아니라, 우리가 실제 제작할 때 쓰는 작업 구조를 관리합니다.

## 들어 있는 것

| 구성 | 역할 |
| --- | --- |
| [실제 제작 사례 3종](case-studies/README.md) | 원본/후보 비교, 분리 레이어, PSD, 생성 원본·실패·재시도와 검수 결과 |
| [제작 스킬](skills/asset-localization/SKILL.md) | 분석·생성·후처리·검수의 순서와 판단 기준 |
| [JSON 예시](skills/asset-localization/references/) | 레이어 분석, 생성 시도, 조립 스펙 |
| `layer-studio` CLI | 원본 복사, 분석 통계, 생성물 보관, PNG·PSD 출력, 무결성 검사 |
| [작업 가이드](docs/workflow.md) | 역할 분담, 폴더 계약, 실패·재시도·승인 기록 |
| [합성 테스트 예제](examples/demo.py) | 게임 이미지나 생성 API 없이 보관·PSD 경로 확인 |
| [검증 기록](docs/verification.md) | 실제 실행한 검사와 확인하지 않은 범위 |

이미지 생성은 에이전트가 사용 가능한 생성 도구로 수행합니다. CLI가 모델을 호출하거나 자동으로 번역·레이어를 추론하지는 않습니다. 사용자가 요청한 실제 사례는 `case-studies/furuyoni/`에 별도 권리 표시와 함께 보관합니다. 전체 게임 파일과 번역 데이터베이스는 포함하지 않습니다.

## 실제 사례: 찬란한 결투

[![Radiant Duels 원본과 찬란한 결투 시험 후보](case-studies/furuyoni/radiant-duels/통합에셋/미리보기.png)](case-studies/furuyoni/radiant-duels/README.md)

7개 레이어, 캐릭터 페이드 마스크, 기본 생성 5회와 재시도 2회를 사용한 메뉴 제작 사례입니다. **원본 일치 기준에 미달한 시험 후보**이며 게임 적용본은 아닙니다. 과정과 실패 이유를 포함해 [원본·레이어·PSD·생성 기록을 확인할 수 있습니다](case-studies/furuyoni/radiant-duels/README.md).

[공격후: 원형 아트와 발광](case-studies/furuyoni/after-attack/README.md) · [동결: 색상과 숨은 RGB 분석](case-studies/furuyoni/ice-counter/README.md)

## 빠르게 실행

Python 3.11 이상이 필요합니다. Windows PowerShell에서 저장소 루트를 기준으로 실행합니다. 별도 가상환경을 사용하므로 기존 게임 패치 환경에 영향을 주지 않습니다.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe examples/demo.py jobs/demo-001
.\.venv\Scripts\layer-studio.exe verify jobs/demo-001/demo-job v001
```

macOS/Linux에서는 `python3 -m venv .venv`, `.venv/bin/python`, `.venv/bin/layer-studio`를 사용합니다. 해당 OS에서의 실행 검증 여부는 검증 기록을 확인하세요.

예제는 직접 만든 단순 도형으로 투명도, 한글 레이어 이름, 레이어 순서, 숨김 상태, PSD 합성을 검사합니다. 실제 현지화 품질이나 이미지 생성 성공을 보여주는 데모는 아닙니다. 기존 폴더가 있으면 `demo-002`처럼 새 이름을 사용하세요.

## 실제 제작에서 쓰기

```powershell
# 1. 원본 바이트 보존 + 분석 통계/밝고 어두운 미리보기
.\.venv\Scripts\layer-studio.exe init work/source.png jobs/menu-001 --asset menu --locale ko

# 2. jobs/menu-001/작업기록/analysis.json을 실제 관찰로 채웁니다.
# 3. 이미지 생성 도구로 레이어를 생성하고 정확한 프롬프트/출처를 기록합니다.
.\.venv\Scripts\layer-studio.exe archive jobs/menu-001 work/call-001.json
.\.venv\Scripts\layer-studio.exe archive jobs/menu-001 work/call-002.json

# 4. 생성 레이어를 원본과 같은 캔버스에 배치하고 처리 레시피를 spec에 남깁니다.
.\.venv\Scripts\layer-studio.exe build jobs/menu-001 work/spec.json
.\.venv\Scripts\layer-studio.exe verify jobs/menu-001 v001
```

`work/`의 JSON은 [예시](skills/asset-localization/references/)를 복사하여 실제 파일명·문구·근거로 채웁니다. 입력 파일 경로는 각각 **그 JSON 파일 위치를 기준**으로 해석합니다. `analysis.json`의 `measurements`는 유지하고 번역·레이어별 색상·관찰·예상 횟수를 추가합니다. `reviewed_by`와 배경 확인 값은 실제로 분석한 뒤 기록합니다.

에이전트에는 저장소의 `skills/asset-localization/SKILL.md`를 읽고 작업하도록 요청하면 됩니다. 설치형 스킬이 필요하면 `asset-localization` 폴더만 해당 도구의 skills 폴더에 복사할 수 있습니다. CLI는 따로 설치해야 합니다. 저장소가 전역 에이전트 설정을 자동 변경하지 않습니다.

## 결과 폴더

```text
jobs/menu-001/
├── job.json
├── 원본에셋/source.png
├── 레이어에셋/v001/*.png
├── 통합에셋/v001/
│   ├── candidate.png
│   ├── source-candidate-dark.png
│   └── source-candidate-light.png
├── menu-v001.psd
└── 작업기록/
    ├── analysis.json
    ├── source-dark.png
    ├── source-light.png
    ├── generations/call-001/
    │   ├── raw.png
    │   ├── reference-01.png
    │   ├── analysis.json
    │   └── record.json
    └── builds/v001/
        ├── analysis.json
        ├── spec.json
        ├── qa.json
        └── manifest.json
```

같은 작업의 수정본은 `v002`로 추가합니다. 원본, 실패 생성물, 예전 조립본을 덮어쓰지 않습니다. 부분 실패 폴더도 남기므로 다른 revision으로 재시도합니다. ZIP은 생성하지 않습니다. 폴더 보관과 외부 백업은 별개이며 백업 서버는 포함하지 않습니다.

## 지켜야 하는 제작 원칙

- 생성 전에 원본 레이어의 색상·알파·순서·효과를 분석합니다. 원본 픽셀 컷아웃, 코드로 글씨 지우기/메우기, 원본 알파 복사는 하지 않습니다.
- 코드 후처리는 생성된 레이어와 측정한 파라미터에 적용합니다. 재사용한 생성물의 출처와 처리 과정을 남깁니다.
- 생성 횟수는 분석 결과에 따라 정하고 재시도를 따로 기록합니다. 실패 출력도 보관할 자산입니다.
- 원본 PNG에서 추론한 계층이며 원래 PSD의 복원은 아닙니다. v0.1 PSD는 개별 래스터 레이어입니다.
- 파일 검사 PASS는 시각 품질·번역·게임 적용·배포 승인과 별개입니다. 결과는 항상 `CANDIDATE`로 생성됩니다.

## 현재 도구 범위

PNG 입력, 동일 크기 풀캔버스 레이어, normal 합성, 레이어 opacity/visibility를 지원합니다. 효과는 별도 PNG로 베이크합니다. 자유 좌표 배치·키잉·색 보정 레시피의 자동 실행, editable text·스마트 오브젝트·별도 마스크·PSD layer effects는 아직 구현하지 않았습니다. 에이전트가 후처리한 파일과 레시피를 입력으로 사용합니다.

`archive`는 한 생성 호출당 한 출력 PNG를 기록합니다. API 호출/비용 집행은 하지 않습니다. 원본과 동일한 파일을 생성물로 등록하는 것은 차단하지만, 변형된 원본 픽셀의 사용 여부를 해시로 증명할 수는 없습니다. 처리 코드와 시각 결과도 함께 검토해야 합니다. JSON의 검토 완료 표시는 작업자의 기록이며 독립 검수 인증이 아닙니다.

## 개발·기여

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

실제 게임 파일 대신 합성 fixture로 파일 보존·잘못된 입력·레이어 합성·검증 실패 경로를 검사합니다. 한 작업 폴더에는 한 writer만 사용하세요. 불필요한 이미지 재생성과 자동 과금, QA 실패를 PASS로 바꾸는 변경은 피합니다. 변경 전 [AGENTS.md](AGENTS.md)를 확인하세요.

## 라이선스와 출처

이 저장소의 코드·설명 문서·스킬은 [MIT](LICENSE)로 제공합니다. 사례의 게임 이미지·생성물·PSD·인용된 게임 문구는 [별도 권리 안내](case-studies/ASSET-RIGHTS.md)를 따르며 MIT에 포함되지 않습니다. 게임 이미지, 상표, 폰트, 번역 데이터 및 외부 도구는 각자의 권리·이용 조건을 따릅니다. 코드 라이선스만으로 특정 게임 에셋의 제작·모금·배포 권한을 얻는 것은 아닙니다.

방법론의 출처와 일반화 과정은 [PROVENANCE.md](PROVENANCE.md), 외부 의존성은 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에 있습니다. 저장소 공개 전에는 코드와 실제 제작 자료의 포함 범위를 다시 확인하세요.
