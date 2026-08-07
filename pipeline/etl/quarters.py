"""분기 라벨 유틸. 라벨('2023Q1') ↔ 서수(2023Q1=0) 변환의 단일 소스.

파일명 표기(202303, 20251030 등)가 분기마다 미묘하게 달라서
디렉터리 라벨(data/raw/2023Q1/)을 정본으로 삼는다 (phase-2 문서 §9).
"""

import re
from pathlib import Path

BASE_YEAR = 2023  # 2023Q1 이전 아카이브는 ID 날짜 오염으로 사용 불가
RAW_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw"


def to_ord(label: str) -> int:
    m = re.fullmatch(r"(\d{4})Q([1-4])", label)
    if not m:
        raise ValueError(f"분기 라벨 형식 오류: {label}")
    return (int(m.group(1)) - BASE_YEAR) * 4 + int(m.group(2)) - 1


def to_label(qord: int) -> str:
    return f"{BASE_YEAR + qord // 4}Q{qord % 4 + 1}"


def available(sido_keyword: str = "서울") -> dict[str, Path]:
    """data/raw/에서 시도 CSV가 준비된 분기 → CSV 경로. 라벨 순 정렬."""
    found = {}
    for d in (sorted(RAW_DIR.iterdir()) if RAW_DIR.exists() else []):
        if not (d.is_dir() and re.fullmatch(r"\d{4}Q[1-4]", d.name)):
            continue
        csvs = [p for p in d.glob("*.csv") if sido_keyword in p.name]
        if csvs:
            found[d.name] = csvs[0]
    return dict(sorted(found.items(), key=lambda kv: to_ord(kv[0])))
