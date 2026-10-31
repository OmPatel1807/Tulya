#!/usr/bin/env python3
"""
acquire_data.py - Autonomous polite data acquisition for Tulya Phase Loop 0A.
Downloads candidate pairs one by one from indiacode.gov.in, waits 3.5s between downloads,
validates each pair with validate_data.py, and updates data/raw/SOURCES.md.
"""

import os
import sys
import time
import requests
from datetime import datetime
from pathlib import Path

# Add backend to path so we can import validate_data
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_data import validate_pair, extract_pdf_pages

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

DATA_RAW = Path("data/raw")
DATA_RAW.mkdir(parents=True, exist_ok=True)

# Candidate definitions with verified bitstream UUIDs from indiacode.gov.in
CANDIDATES = [
    {
        "slug": "environment_protection_1986",
        "name": "The Environment (Protection) Act, 1986",
        "act_no": 29,
        "year": 1986,
        "category": "short",
        "en_url": "https://indiacode.gov.in/server/api/core/bitstreams/2eeec562-717d-4070-b70e-a91a4269c9ca/content",
        "hi_url": "https://indiacode.gov.in/server/api/core/bitstreams/49244718-9d6b-4c5a-8884-17cd0c49bcd7/content"
    },
    {
        "slug": "right_to_education_2009",
        "name": "The Right of Children to Free and Compulsory Education Act, 2009",
        "act_no": 35,
        "year": 2009,
        "category": "short",
        "en_url": "https://indiacode.gov.in/server/api/core/bitstreams/1698afc1-10ba-4a24-91c1-e20c01ce9237/content",
        "hi_url": "https://indiacode.gov.in/server/api/core/bitstreams/a35b64fa-5a20-4af5-879e-45fdd61005e9/content"
    },
    {
        "slug": "domestic_violence_2005",
        "name": "The Protection of Women from Domestic Violence Act, 2005",
        "act_no": 43,
        "year": 2005,
        "category": "short_medium",
        "en_url": "https://indiacode.gov.in/server/api/core/bitstreams/6b88d866-050f-4779-a212-6676d85e1519/content",
        "hi_url": "https://indiacode.gov.in/server/api/core/bitstreams/d1926cd1-d341-4586-9019-03d5f6379e66/content"
    },
    {
        "slug": "right_to_information_2005",
        "name": "The Right to Information Act, 2005",
        "act_no": 22,
        "year": 2005,
        "category": "medium",
        "en_url": "https://indiacode.gov.in/server/api/core/bitstreams/78f68a27-8902-4081-8d53-a3932264ca52/content",
        "hi_url": "https://indiacode.gov.in/server/api/core/bitstreams/3cfec817-8b3b-4fc4-9395-f04bfcca1a1f/content"
    },
    {
        "slug": "consumer_protection_2019",
        "name": "The Consumer Protection Act, 2019",
        "act_no": 35,
        "year": 2019,
        "category": "medium",
        "en_url": "https://indiacode.gov.in/server/api/core/bitstreams/b5ba879f-4662-458c-b5d3-dae377ff92e0/content",
        "hi_url": "https://indiacode.gov.in/server/api/core/bitstreams/a4008e1f-39ef-4859-98ed-613ccdd2c835/content"
    },
    {
        "slug": "contract_act_1872",
        "name": "The Indian Contract Act, 1872",
        "act_no": 9,
        "year": 1872,
        "category": "medium_long",
        "en_url": "https://indiacode.gov.in/server/api/core/bitstreams/e7571d39-11a7-4a2c-86e3-c515ae43e617/content",
        "hi_url": "https://indiacode.gov.in/server/api/core/bitstreams/b8516d55-a010-4616-91b3-954251074b2c/content"
    },
    {
        "slug": "constitution_of_india",
        "name": "The Constitution of India",
        "act_no": None,
        "year": 1950,
        "category": "constitution",
        "en_url": "https://indiacode.gov.in/server/api/core/bitstreams/2bd776ff-891e-444c-9344-f63df7b299fc/content",
        "hi_url": "https://indiacode.gov.in/server/api/core/bitstreams/c83e9912-5843-450f-8d17-200ad52425cb/content"
    }
]

def download_file(url: str, dest_path: Path) -> bool:
    """Download a file with polite headers and error handling."""
    print(f"Downloading {dest_path.name} from {url}...")
    try:
        resp = requests.get(url, headers=HEADERS, stream=True, timeout=30)
        if resp.status_code != 200:
            print(f"FAILED: HTTP status {resp.status_code}")
            return False
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=16384):
                f.write(chunk)
        print(f"Saved {dest_path.name} ({dest_path.stat().st_size} bytes)")
        return True
    except Exception as e:
        print(f"Download exception: {e}")
        return False

def acquire_candidate(cand: dict) -> dict:
    slug = cand["slug"]
    en_file = DATA_RAW / f"{slug}_en.pdf"
    hi_file = DATA_RAW / f"{slug}_hi.pdf"
    
    # Download EN
    if not en_file.exists():
        time.sleep(3.5)  # Be polite: >= 3 seconds between requests
        ok = download_file(cand["en_url"], en_file)
        if not ok:
            return {"slug": slug, "status": "FAILED_DOWNLOAD_EN"}
    
    # Download HI
    if not hi_file.exists():
        time.sleep(3.5)  # Be polite: >= 3 seconds between requests
        ok = download_file(cand["hi_url"], hi_file)
        if not ok:
            return {"slug": slug, "status": "FAILED_DOWNLOAD_HI"}
            
    # Run verifier
    val = validate_pair(slug, str(en_file), str(hi_file))
    val["category"] = cand["category"]
    val["name"] = cand["name"]
    val["act_no"] = cand["act_no"]
    val["year"] = cand["year"]
    val["en_url"] = cand["en_url"]
    val["hi_url"] = cand["hi_url"]
    val["en_size"] = en_file.stat().st_size if en_file.exists() else 0
    val["hi_size"] = hi_file.stat().st_size if hi_file.exists() else 0
    val["retrieved_date"] = datetime.now().strftime("%Y-%m-%d")
    
    if not val["usable"]:
        print(f"REJECTED: {slug} reason: {val['reason']}")
        # Clean up failed download
        if en_file.exists():
            en_file.unlink()
        if hi_file.exists():
            hi_file.unlink()
    else:
        print(f"ACCEPTED: {slug} | EN pages: {val['en_pages']}, HI pages: {val['hi_pages']} | Verdict: {val['verdict_hi']}")
        
    return val

if __name__ == "__main__":
    results = []
    for cand in CANDIDATES:
        print(f"\n--- Processing Candidate: {cand['name']} ---")
        res = acquire_candidate(cand)
        results.append(res)
    
    print("\n\nAll candidate processing complete.")
