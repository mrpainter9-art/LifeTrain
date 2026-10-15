# 실제 지형 → 도트 시차 레이어

기차 창가 높이에서 호수 쪽 창밖을 본 풍경을 고도 데이터로 렌더해 원경/중경/근경 PNG 띠로 만든다.
자세한 방식과 한계는 `docs/DESIGN.md` 4장.

```
pip install numpy pillow
python3 fetch_tiles.py   # AWS Terrain Tiles z12, bbox.txt 범위
python3 render.py        # far/mid/near.png, *_water.png, manifest.json
python3 export.py        # *_wa.png (반사용 물 마스크), 봉우리 화면 높이
python3 prev.py 57000 63000 70000 78500   # prev.png 미리보기
cp far.png mid.png near.png mid_wa.png near_wa.png manifest.json ../../assets/terrain/brienz/
```
