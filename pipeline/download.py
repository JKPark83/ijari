"""분기별 상가(상권)정보 zip 다운로드.

공공데이터포털(15083033)의 '주기성 과거 데이터' uddi를 분기 라벨로 매핑해 둔다.
uddi → selectFileDataDownload.do(JSON) → atchFileId → cmm/cmm/fileDownload.do 순서로
실제 파일 URL을 해석한다. 새 분기가 공개되면 QUARTERS에 한 줄 추가.

사용:
    uv run python download.py 2026Q1            # 한 분기
    uv run python download.py 2023Q1 2023Q2 ... # 여러 분기
    uv run python download.py --list            # 매핑 목록
"""

import json
import sys
import urllib.request
import zipfile
from pathlib import Path

DATASET_PK = "15083033"
PORTAL = "https://www.data.go.kr"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": f"{PORTAL}/data/{DATASET_PK}/fileData.do",
}

# 2023Q1 이전 아카이브는 오염(ID 날짜 오염)으로 확정 — 매핑에 넣지 않는다.
QUARTERS: dict[str, str] = {
    "2023Q1": "uddi:e311a913-1fca-4473-966b-87b40f4772f0",  # 20230331
    "2023Q2": "uddi:30cccb49-5af5-4a96-ad70-81fe007c2039",  # 20230630
    "2023Q3": "uddi:347b0e40-0648-46b2-8625-af9419bdf8d5",  # 20230930
    "2023Q4": "uddi:798b6f4a-18f9-4c6c-b4e7-9054a9d8bbf4",  # 20231231
    "2024Q1": "uddi:52b7eac4-fe84-4357-88f5-a842ccc4d1cd",  # 20240331
    "2024Q2": "uddi:4e95c557-240a-45cd-ab99-e631763a9f1c",  # 20240630
    "2024Q3": "uddi:b5774885-a961-41a0-9e17-ac43087a3767",  # 20240930
    "2024Q4": "uddi:9cefeea7-4b0a-4817-ae7c-9f79ca2c7cfd",  # 20241231
    "2025Q1": "uddi:86a02b73-c0ce-447f-a492-f99490392056",  # 20250331
    "2025Q2": "uddi:e61bf1be-7a4c-400a-99a7-f91543ca64ca",  # 20250630
    "2025Q3": "uddi:05123ff0-e436-40f2-9814-ad1ac0ae4be4",  # 20251030 (포털 표기 기준)
    "2025Q4": "uddi:9a136460-5faf-4ab7-a887-8c2b425274e4",  # 20251231
    "2026Q1": "uddi:6a450671-390c-4b6d-979c-fa056a627084",  # 20260331 — 현재 메인 파일
}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=600) as resp:
        return resp.read()


def resolve(uddi: str) -> tuple[str, str]:
    """uddi → (다운로드 URL, 원본 파일명)."""
    meta_url = (
        f"{PORTAL}/tcs/dss/selectFileDataDownload.do"
        f"?publicDataPk={DATASET_PK}&publicDataDetailPk={uddi}"
    )
    meta = json.loads(_get(meta_url))

    def walk(obj):
        if isinstance(obj, dict):
            if obj.get("atchFileId") and obj.get("orginlFileNm"):
                return obj
            for v in obj.values():
                if (found := walk(v)) is not None:
                    return found
        elif isinstance(obj, list):
            for v in obj:
                if (found := walk(v)) is not None:
                    return found
        return None

    info = walk(meta)
    if info is None:
        raise RuntimeError(f"{uddi}: 응답에서 atchFileId를 찾지 못함 — 포털 구조 변경 의심")
    url = (
        f"{PORTAL}/cmm/cmm/fileDownload.do"
        f"?atchFileId={info['atchFileId']}&fileDetailSn={info.get('fileDetailSn', 1)}"
    )
    return url, info["orginlFileNm"]


def download(quarter: str) -> Path:
    uddi = QUARTERS.get(quarter)
    if uddi is None:
        sys.exit(f"{quarter}: 매핑 없음. 포털에서 uddi를 확인해 QUARTERS에 추가할 것")
    dest_dir = RAW_DIR / quarter
    dest_dir.mkdir(parents=True, exist_ok=True)

    url, filename = resolve(uddi)
    dest = dest_dir / filename
    if dest.exists() and dest.stat().st_size > 0:
        print(f"{quarter}: 이미 있음 → {dest.name} ({dest.stat().st_size:,} bytes)")
        return dest

    print(f"{quarter}: 다운로드 시작 → {filename}")
    data = _get(url)
    if not data.startswith(b"PK"):
        raise RuntimeError(f"{quarter}: zip이 아닌 응답({len(data)} bytes) — 링크 만료/변경 의심")
    dest.write_bytes(data)
    print(f"{quarter}: 완료 ({len(data):,} bytes)")
    return dest


def extract_sido(zip_path: Path, sido_keyword: str) -> list[Path]:
    """zip에서 특정 시도 CSV만 추출. 구형 zip은 파일명이 CP949라 되돌려 읽는다."""
    out = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename
            try:
                name = name.encode("cp437").decode("cp949")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
            if sido_keyword in name and name.endswith(".csv"):
                dest = zip_path.parent / Path(name).name
                with zf.open(info) as src, open(dest, "wb") as f:
                    while chunk := src.read(1 << 20):
                        f.write(chunk)
                print(f"추출: {dest} ({info.file_size:,} bytes)")
                out.append(dest)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args == ["--list"]:
        for q, u in QUARTERS.items():
            print(q, u)
        if not args:
            print("\n사용: uv run python download.py <분기 라벨>...")
        sys.exit(0)
    for q in args:
        download(q)
