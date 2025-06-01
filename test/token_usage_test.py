#!/usr/bin/env python3
"""
Token Usage Test Script for web2md

This script reads queries from test/queries.txt and makes requests to web2md
to measure token usage for different types of websites.
"""

import httpx
import time
import json
import os
from typing import List, Dict, Tuple
from urllib.parse import urlencode

WEB2MD_BASE_URL = "http://localhost:7001"
NUM_RESULTS = 3
DELAY_BETWEEN_REQUESTS = 2

def estimate_tokens(text: str) -> int:
    return len(text) // 4

def read_queries(file_path: str) -> Tuple[List[str], List[str]]:
    normal_queries = []
    docs_queries = []
    current_section = None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    if 'Normal Web Search' in line:
                        current_section = 'normal'
                    elif 'Documentation/Technical' in line:
                        current_section = 'docs'
                    continue
                
                if current_section == 'normal':
                    normal_queries.append(line)
                elif current_section == 'docs':
                    docs_queries.append(line)
    
    except FileNotFoundError:
        print(f"Error: {file_path} not found!")
        return [], []
    
    return normal_queries, docs_queries

def make_web2md_request(query: str, num_results: int = NUM_RESULTS) -> Dict:
    params = {
        'q': query,
        'num_results': num_results,
        'format': 'json'
    }
    
    url = f"{WEB2MD_BASE_URL}/?{urlencode(params)}"
    
    try:
        print(f"  Making request: {query}")
        response = httpx.get(url, timeout=60)
        response.raise_for_status()
        
        response_text = response.text
        token_count = estimate_tokens(response_text)
        
        return {
            'query': query,
            'success': True,
            'response_length': len(response_text),
            'estimated_tokens': token_count,
            'status_code': response.status_code
        }
    
    except httpx.RequestError as e:
        print(f"  Error making request: {e}")
        return {
            'query': query,
            'success': False,
            'error': str(e),
            'estimated_tokens': 0
        }

def run_test_suite(queries: List[str], category: str) -> Dict:
    print(f"\n=== Testing {category} Queries ===")
    results = []
    total_tokens = 0
    successful_requests = 0
    
    for i, query in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] Testing: {query}")
        
        result = make_web2md_request(query)
        results.append(result)
        
        if result['success']:
            total_tokens += result['estimated_tokens']
            successful_requests += 1
            print(f"  ✓ Success: {result['estimated_tokens']:,} tokens")
        else:
            print(f"  ✗ Failed: {result.get('error', 'Unknown error')}")
        
        if i < len(queries):
            time.sleep(DELAY_BETWEEN_REQUESTS)
    
    avg_tokens = total_tokens / successful_requests if successful_requests > 0 else 0
    
    stats = {
        'category': category,
        'total_queries': len(queries),
        'successful_requests': successful_requests,
        'failed_requests': len(queries) - successful_requests,
        'total_tokens': total_tokens,
        'average_tokens_per_query': avg_tokens,
        'results': results
    }
    
    return stats

def print_summary(normal_stats: Dict, docs_stats: Dict):
    print("\n" + "="*60)
    print("TOKEN USAGE SUMMARY")
    print("="*60)
    
    for stats in [normal_stats, docs_stats]:
        category = stats['category']
        print(f"\n{category.upper()} WEBSITES:")
        print(f"  Total queries: {stats['total_queries']}")
        print(f"  Successful: {stats['successful_requests']}")
        print(f"  Failed: {stats['failed_requests']}")
        print(f"  Total tokens: {stats['total_tokens']:,}")
        print(f"  Average tokens per query: {stats['average_tokens_per_query']:,.0f}")
        
        if stats['successful_requests'] > 0:
            successful_results = [r for r in stats['results'] if r['success']]
            tokens = [r['estimated_tokens'] for r in successful_results]
            print(f"  Min tokens: {min(tokens):,}")
            print(f"  Max tokens: {max(tokens):,}")
    
    if normal_stats['successful_requests'] > 0 and docs_stats['successful_requests'] > 0:
        normal_avg = normal_stats['average_tokens_per_query']
        docs_avg = docs_stats['average_tokens_per_query']
        difference = docs_avg - normal_avg
        percentage = (difference / normal_avg) * 100 if normal_avg > 0 else 0
        
        print(f"\nCOMPARISON:")
        print(f"  Documentation sites use {difference:+,.0f} tokens on average")
        print(f"  That's {percentage:+.1f}% compared to normal websites")

def save_detailed_results(normal_stats: Dict, docs_stats: Dict, output_file: str):
    detailed_results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'configuration': {
            'web2md_url': WEB2MD_BASE_URL,
            'num_results_per_query': NUM_RESULTS,
            'delay_between_requests': DELAY_BETWEEN_REQUESTS
        },
        'normal_websites': normal_stats,
        'documentation_websites': docs_stats
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed results saved to: {output_file}")

def main():
    print("Web2MD Token Usage Test")
    print("=" * 30)
    
    try:
        response = httpx.get(WEB2MD_BASE_URL, timeout=5)
        print(f"✓ web2md is running at {WEB2MD_BASE_URL}")
    except httpx.RequestError:
        print(f"✗ Error: web2md is not accessible at {WEB2MD_BASE_URL}")
        print("Please make sure web2md is running before running this test.")
        return
    
    queries_file = os.path.join(os.path.dirname(__file__), 'queries.txt')
    normal_queries, docs_queries = read_queries(queries_file)
    
    if not normal_queries and not docs_queries:
        print("No queries found in queries.txt")
        return
    
    print(f"Found {len(normal_queries)} normal queries and {len(docs_queries)} docs queries")
    
    normal_stats = run_test_suite(normal_queries, "Normal")
    docs_stats = run_test_suite(docs_queries, "Documentation")
    
    print_summary(normal_stats, docs_stats)
    
    output_file = os.path.join(os.path.dirname(__file__), 'token_usage_results.json')
    save_detailed_results(normal_stats, docs_stats, output_file)

if __name__ == "__main__":
    main()