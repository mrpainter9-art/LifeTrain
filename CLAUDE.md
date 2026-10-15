# LifeTrain

- 사용자는 코딩 경험이 없는 게임 기획자. 답은 한국어로, 쉬운 말로.
- 게임 설계와 지금까지의 결정은 `docs/DESIGN.md`가 기준. 바꾸는 결정이 생기면 그 문서도 같이 고친다.
- Godot 4.7 프로젝트 (project.godot). 도트 그래픽이라 텍스처 필터는 Nearest, 내부 해상도 560x240.
- `prototype/web/train.html`이 동작하는 기준 구현이다. Godot로 옮길 때 값(노선, 레이어 계수, 조명색, 대사)은 여기서 가져온다.
- 실제 지형 레이어는 `tools/terrain/`에서 만들고 결과만 `assets/terrain/<구간>/`에 둔다. 고도 타일은 커밋하지 않는다.
