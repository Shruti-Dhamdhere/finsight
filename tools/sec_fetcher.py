import requests
import json
import time
import re
import os
import config

# SEC EDGAR requires a user agent header by law
HEADERS = {
    "User-Agent": "FinSight Research Tool contact@finsight.com",
    "Accept-Encoding": "gzip, deflate",
    "Host": "data.sec.gov"
}

def get_cik_from_ticker(ticker: str) -> str:
    """Convert stock ticker to SEC CIK number."""
    print(f"  [RAG Agent] Looking up SEC CIK for {ticker}...")
    
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(url, headers={
            "User-Agent": "FinSight Research Tool contact@finsight.com"
        })
        data = response.json()
        
        for key, company in data.items():
            if company["ticker"].upper() == ticker.upper():
                cik = str(company["cik_str"]).zfill(10)
                print(f"  [RAG Agent] Found CIK: {cik}")
                return cik
                
        return None
    except Exception as e:
        print(f"  [RAG Agent] CIK lookup failed: {e}")
        return None


def get_recent_filings(cik: str, filing_type: str = "10-K", count: int = 2) -> list:
    """Get list of recent SEC filings for a company."""
    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accession_numbers = filings.get("accessionNumber", [])
        filing_dates = filings.get("filingDate", [])
        
        results = []
        for i, form in enumerate(forms):
            if form == filing_type and len(results) < count:
                results.append({
                    "type": form,
                    "accession_number": accession_numbers[i],
                    "date": filing_dates[i],
                    "cik": cik
                })
                
        return results
    except Exception as e:
        print(f"  [RAG Agent] Filing lookup failed: {e}")
        return []


def extract_filing_text(cik: str, accession_number: str) -> str:
    """Extract text content from an SEC filing."""
    try:
        # Format accession number for URL
        acc_formatted = accession_number.replace("-", "")
        
        # Get filing index
        index_url = f"https://www.sec.gov/Archives/edgar/full-index/{cik[:4]}"
        
        # Direct document fetch
        doc_url = (
            f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{acc_formatted}/{accession_number}-index.htm"
        )
        
        response = requests.get(doc_url, headers={
            "User-Agent": "FinSight Research Tool contact@finsight.com"
        })
        
        # Extract text links from index
        text = response.text
        
        # Find the main document
        import re
        links = re.findall(r'href="(/Archives/edgar/data/[^"]+\.htm)"', text)
        
        if not links:
            return ""
            
        # Fetch main document
        main_url = f"https://www.sec.gov{links[0]}"
        time.sleep(0.1)  # SEC rate limit courtesy
        
        doc_response = requests.get(main_url, headers={
            "User-Agent": "FinSight Research Tool contact@finsight.com"
        })
        
        # Clean HTML tags
        clean_text = re.sub(r'<[^>]+>', ' ', doc_response.text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Return first 50,000 chars (enough for key sections)
        return clean_text[:50000]
        
    except Exception as e:
        print(f"  [RAG Agent] Text extraction failed: {e}")
        return ""


def get_sec_filings_text(ticker: str) -> dict:
    """
    Main function: fetches recent 10-K and 10-Q filings for a ticker.
    Returns extracted text ready for RAG processing.
    """
    print(f"  [RAG Agent] Fetching SEC filings for {ticker}...")
    
    cik = get_cik_from_ticker(ticker)
    if not cik:
        return {"error": f"Could not find SEC CIK for {ticker}", "status": "failed"}
    
    all_filings = []
    
    for filing_type in config.SEC_FILING_TYPES:
        filings = get_recent_filings(cik, filing_type, config.MAX_FILINGS)
        
        for filing in filings:
            print(f"  [RAG Agent] Extracting {filing_type} from {filing['date']}...")
            text = extract_filing_text(cik, filing["accession_number"])
            
            if text:
                all_filings.append({
                    "type": filing_type,
                    "date": filing["date"],
                    "text": text,
                    "accession_number": filing["accession_number"]
                })
            
            time.sleep(0.2)  # Be respectful to SEC servers
    
    if not all_filings:
        return {
            "ticker": ticker,
            "error": "No filing text could be extracted",
            "status": "failed"
        }
    
    print(f"  [RAG Agent] Successfully fetched {len(all_filings)} filings")
    
    return {
        "ticker": ticker,
        "cik": cik,
        "filings": all_filings,
        "total_filings": len(all_filings),
        "status": "success"
    }