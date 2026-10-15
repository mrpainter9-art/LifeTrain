# 창가석 기차 여행: 설계 정리 (Godot 이전용)

웹 프로토타입(버전 3): `prototype/web/train.html` (게시본: https://claude.ai/artifact/JS5wxcYLjiwXr9L2JbJpHH)
실제 지형 레이어 결과물: `assets/terrain/brienz/` (낮/노을/밤 비교: `docs/images/brienzersee-day-dusk-night.png`)
레퍼런스 이미지: `docs/images/reference.png` (기차 창밖의 알프스, 호수, 교회 마을, 빨간 기차, 꽃 들판, 보온병과 책이 놓인 창가 테이블)

## 1. 게임 콘셉트 (확정된 것)
- 실제 노선(루체른 → 인터라켄 오스트, 골든패스 루트 중 Luzern–Interlaken 구간)을 달리는 조용한 횡스크롤 도트 게임.
- 기차 안은 보이지 않아도 된다. 큰 창, 창틀, 좌석 모서리, 테이블(보온병과 책)만 보이고 중요한 건 창밖 풍경.
- 시간과 날씨는 현실 시간 기준(Europe/Zurich). 해 위치는 실제 천문 계산, 날씨는 40분 단위 결정적 블록.
- 게임 내 시간이 빠르거나 느리게 흐르지 않는다. 강화, 수집, 성장 없음. (프로토타입에만 x8, x40 빨리감기 버튼)
- 승객은 보이지 않고 대사로만 존재. 작은 이야기 3개:
  - 마르그리트: 뜨개질하는 할머니, 루체른~룽게른
  - 노아: 견습 산악 가이드, 헤르기스빌~마이링겐
  - 엘리프: 아버지의 흑백 사진 속 호수를 찾는 여행자, 자르넨~종점
- 상호작용: 말 걸기, 차 나눠 주기, 뜨개실 잡아 주기, 잠든 엘리프를 브리엔츠 호수에서 깨워 주기.
- 정차 티켓: 여행당 1장. 원하는 곳에서 5분 동안 기차를 세운다.
- 엽서: 지금 창밖 스냅샷과 장소, 고도, 현지 시각, 날씨를 담은 엽서. 위치에 고정되어 다른 사람이 같은 지점을 지날 때 보이고, 좋아요를 누를 수 있다. 이미지 저장, 메일, 문자로 공유 가능.

## 2. 노선 데이터 (prototype/web/train.html 안의 상수)
- `ST` 역 목록 (s = 루체른부터의 거리, 미터):
  - Luzern 0, Hergiswil 8000, Alpnachstad 14000, Sarnen 21500, Giswil 29800
  - Lungern 37000, Brünig-Hasliberg 44200, Meiringen 53000
  - Brienz 64907, Interlaken Ost 79649 (이 두 역은 실제 지형 기준으로 보정됨)
- `LEGV` 구간 속도(km/h): 55,55,60,60,35,25,25,60,65. 브뤼니히 고개 구간은 톱니궤도라 느림.
- 정차 시간: 출발역 90초, 중간역 60초. 사다리꼴 가감속.
- `SEGS`: 구간 종류(city/lake/village/meadow/forest/pasture)와 호수 이름, 색.
- `TUN`: 터널 구간. `CURVES`: 곡선 구간(앞쪽에 우리 기차가 보임).
- `PASS`, `BEATS`: 승객 탑승 구간과 거리별 대사. 이전에 한 행동(flags)에 따라 대사가 달라짐.

## 3. 화면과 레이어 구조 (Godot로 옮길 때 그대로 쓰면 됨)
- 내부 해상도 560x240, 픽셀 확대(nearest).
- 시차 레이어. 계수 F는 px/m로, 화면 x = (월드 s − 현재 s)·F + 330.
  - 하늘 그라데이션, 별, 해, 무지개, 구름(낮/노을/밤 팔레트 3종)
  - 원경 F=0.01625 (실제 지형 far.png)
  - 중경 F=0.065 (mid.png)
  - 근경 F=0.26 (near.png, 호수 포함)
  - 호숫가 마을과 나무 F=0.5 (절차적)
  - 앞 들판, 꽃, 울타리 F=1.3 (절차적)
  - 아주 가까운 나무 F=3, 터널
  - 창틀과 테이블 (고정, 조명색만 바뀜)
- 실제 지형이 없는 구간(루체른~마이링겐)은 아직 절차적 산으로 그린다. 마이링겐 직전 600m에서 실제 지형으로 크로스페이드.
- 조명: 그림은 전부 맑은 낮 기준으로 만든다. 해 고도에 따라 땅 레이어 위에 색을 덮어 아침, 노을, 밤을 만든다 (`tintFor`, source-atop). 밤에는 창문 불빛 점을 추가한다.
- 호수 반사: 열마다 물이 시작되는 줄(물가선)을 기준으로 위쪽 풍경을 뒤집어 45% 알파로 그리고, 물 마스크로 자른다. 반짝임과 해 그림자, 돛단배도 있다.
- 봉우리 이름: 실제 좌표로 계산한 위치(manifest.peaks의 s, 거리 d, 화면 y). 앞 레이어에 가려지면 표시하지 않는다.

## 4. 실제 풍경 → 도트 파이프라인 (tools/terrain/)
1. **고도 데이터**: AWS Terrain Tiles (terrarium, z12, 약 26m/px). `python3 fetch_tiles.py`로 120장을 받는다 (범위는 bbox.txt: x 2133–2144, y 1443–1452). 타일은 저장소에 넣지 않는다.
   - 높이 = R·256 + G + B/256 − 32768
2. **철로**: 웨이포인트를 손으로 찍고 Chaikin 스무딩. 마이링겐 → 브리엔츠 → 호수 북쪽 → 인터라켄 오스트.
   - OSM(overpass)이 막혀 있어서 그렇게 했다. 새 환경에서는 OSM 실제 선로로 교체할 것.
3. **render.py**: 기차 창 높이에서 왼쪽(남쪽)을 보는 슬릿스캔 렌더.
   - 원경과 중경은 고정 시선 방향을 쓴다. 평행 광선이라 세로 줄무늬가 생기지 않는다.
   - 근경은 ±2.5km 현(chord) 방향을 쓴다.
   - 지구 곡률과 굴절 0.87, 수직 과장 1.25, 각 층 시작 거리보다 가까운 지형은 눈높이 아래로 눌러 벽이 생기지 않게 한다.
   - 재질(눈, 바위, 고산초지, 숲, 초원)은 고도와 경사로 정하고, 3단계 셰이딩(아트용 광원 방위 330°, 고도 45°)과 거리 안개를 적용한다.
   - 마지막에 40색 양자화와 가로 최빈값 필터를 적용한다.
   - 출력: `far.png`, `mid.png`, `near.png` (RGBA), `*_water.png`, `manifest.json` (레이어 F, s0, 폭, 봉우리, 선로 좌표).
4. **export.py**: 물 마스크를 RGBA로 만들고 봉우리 화면 높이를 계산한다.
5. **prev.py**: 여러 지점의 레이어를 합성해 미리보기 (`python3 prev.py 57000 63000 70000 78500`).
- 실행 순서: `fetch_tiles.py` → `render.py` → `export.py` → (확인) `prev.py`. 결과 PNG와 manifest.json을 `assets/terrain/<구간>/`으로 복사한다.
- 의존성: Python 3, numpy, Pillow. 블렌더 없이 동작한다.

### 알려진 한계와 다음 개선
- swisstopo(wmts.geo.admin.ch, data.geo.admin.ch)와 overpass-api.de가 이전 환경에서 막혀 있었다. 새 환경에서 열려 있다면 다음을 교체하는 게 1순위:
  - swissALTI3D 또는 DHM25 고해상도 고도
  - SWISSIMAGE 항공사진 색
  - OSM 실제 선로
- 26m 해상도라 세부가 뭉툭하고, 회색 바위 덩어리가 실제보다 크다.
- 나머지 구간(루체른~마이링겐)도 같은 방식으로 만들어야 한다.
- 손 보정(도트 터치업) 단계는 아직 없다.

## 5. Godot 4 이전 계획 (제안, 아직 시작 전)
- **첫 설정**: 기본 텍스처 필터 Nearest, 내부 해상도 560x240 SubViewport(또는 viewport 크기 560x240 + stretch mode viewport, 정수 배율).
- **씬 구성**:
  - `Main` (SubViewport 560x240, nearest 확대)
  - `Sky` (셰이더: 해 고도별 그라데이션, 별)
  - `Clouds`
  - `Parallax2D` 레이어 여러 개 (원경, 중경, 근경, 호숫가, 들판, 가까운 나무). 각 레이어의 scroll_scale을 위 F에 맞춘다. 실제 지형 레이어는 긴 텍스처 한 장씩.
  - `WindowFrame` (고정)
  - UI (자막, 안내방송, 버튼)
- **조명**: CanvasModulate 대신 땅 레이어에만 적용되는 셰이더 uniform 색과 세기 (`tintFor`의 값을 그대로 사용). 밤 불빛은 별도 additive 레이어.
- **호수 반사**: 화면 읽기(`hint_screen_texture`) 셰이더로 물가선 기준 뒤집기. 물 마스크 텍스처 사용.
- **시간**: `Time.get_unix_time_from_system()`으로 현실 시간을 쓰고, 해 위치 공식은 `sun()`을 그대로 옮긴다. 타임존은 Europe/Zurich 고정 오프셋(서머타임 규칙 포함)으로 처리.
- **진행 상태**: Autoload `TripState` (start, rBase, tBase, speed, ticketR, flags, fired, log). 저장은 `user://`.
- **엽서와 좋아요 공유**: 웹 버전은 Claude 아티팩트 DB를 썼다. Godot에서는 별도 백엔드(예: Supabase나 Firebase)가 필요하다. 아직 정하지 않았다.
- **웹 내보내기**: Godot 웹 빌드로도 브라우저에서 돌릴 수 있다.

## 6. 폴더 구조
- `docs/`: 이 문서와 이미지
- `prototype/web/`: HTML 프로토타입 (브라우저로 열면 동작. 엽서 공유 DB는 게시본에서만, 로컬에선 브라우저 저장소로 대체)
- `tools/terrain/`: 실제 지형 → 도트 레이어 파이프라인
- `assets/terrain/brienz/`: 마이링겐~인터라켄 오스트 구간 레이어 (far/mid/near, 물 마스크 *_wa, manifest.json)
- `prototype/`, `tools/`, `docs/`에는 `.gdignore`가 있어 Godot가 가져오지 않는다.
