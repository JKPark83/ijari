"""분기 라벨 유틸. 라벨('2023Q1') ↔ 서수(2023Q1=0) 변환의 단일 소스.

파일명 표기(202303, 20251030 등)가 분기마다 미묘하게 달라서
디렉터리 라벨(data/raw/2023Q1/)을 정본으로 삼는다 (phase-2 문서 §9).
"""

import os
import re
import unicodedata
from pathlib import Path

BASE_YEAR = 2023  # 2023Q1 이전 아카이브는 ID 날짜 오염으로 사용 불가
# 전국 CSV는 용량 문제로 외장(T31)에 둔다 — IJARI_RAW_DIR로 위치를 바꾼다
RAW_DIR = Path(os.environ.get("IJARI_RAW_DIR")
               or Path(__file__).resolve().parent.parent.parent / "data" / "raw")


def to_ord(label: str) -> int:
    m = re.fullmatch(r"(\d{4})Q([1-4])", label)
    if not m:
        raise ValueError(f"분기 라벨 형식 오류: {label}")
    return (int(m.group(1)) - BASE_YEAR) * 4 + int(m.group(2)) - 1


def to_label(qord: int) -> str:
    return f"{BASE_YEAR + qord // 4}Q{qord % 4 + 1}"


def available(sido_keyword: str = "서울") -> dict[str, list[Path]]:
    """data/raw/에서 시도 CSV가 준비된 분기 → CSV 경로 목록. 라벨 순 정렬.

    '전국'이면 전 시도 파일을 모은다. ExFAT의 AppleDouble(._*)과
    포털 zip에 섞인 안내 파일([필독]…csv)은 데이터가 아니라서 거른다.
    """
    found = {}
    for d in (sorted(RAW_DIR.iterdir()) if RAW_DIR.exists() else []):
        if not (d.is_dir() and re.fullmatch(r"\d{4}Q[1-4]", d.name)):
            continue
        # macOS가 파일명을 NFD(자모 분해형)로 돌려줄 수 있어 NFC로 맞춰 비교한다
        csvs = sorted(
            p for p in d.glob("*.csv")
            if "상가(상권)정보" in unicodedata.normalize("NFC", p.name)
            and not p.name.startswith("._")
            and (sido_keyword == "전국"
                 or sido_keyword in unicodedata.normalize("NFC", p.name))
        )
        if csvs:
            found[d.name] = csvs
    return dict(sorted(found.items(), key=lambda kv: to_ord(kv[0])))
