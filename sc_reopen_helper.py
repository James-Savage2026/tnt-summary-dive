#!/usr/bin/env python3
"""Service Channel Work Order Reopen Helper

This script helps reopen Service Channel work orders that are failing PM criteria.
Workflow:
1. Click "Edit Work Order" button
2. Change status dropdown from "Completed" to "In Progress"
3. Add notes about which test is failing
4. Save
"""

import csv
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Load Critical Reopen WOs
DATA_PATH = Path.home() / 'bigquery_results' / 'wtw-pm-scores-crystal-method-20260205-221427.csv'
SC_URL = 'https://www.servicechannel.com/sc/wo/Workorders/index?id='

def load_critical_reopen_wos():
    """Load work orders that need to be reopened (Completed + PM < 90% + not Div1)"""
    wos = []
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get('status_name') == 'COMPLETED' and 
                row.get('overall_pass') == 'FAIL' and 
                row.get('is_div1') == 'N'):
                pm_score = float(row.get('pm_score', 0) or 0)
                if pm_score < 90:
                    wos.append({
                        'tracking': row.get('tracking_nbr'),
                        'workorder': row.get('workorder_nbr'),
                        'store': row.get('store_nbr'),
                        'city': row.get('city_name'),
                        'state': row.get('state_cd'),
                        'pm_score': pm_score,
                        'tnt': float(row.get('tnt_score') or 0),
                        'tnt_pass': row.get('tnt_pass'),
                        'rack': float(row.get('rack_score') or 0),
                        'rack_pass': row.get('rack_pass'),
                        'ahu': float(row.get('ahu_tnt_score') or 0),
                        'ahu_pass': row.get('ahu_pass'),
                    })
    return wos

def generate_reopen_notes(wo):
    """Generate notes about which tests are failing"""
    failing = []
    
    if wo['tnt_pass'] == 'FAIL':
        failing.append(f"TnT: {wo['tnt']:.1f}% (needs ≥90%)")
    if wo['rack_pass'] == 'FAIL':
        failing.append(f"Rack: {wo['rack']:.1f}% (needs ≥90%)")
    if wo['ahu_pass'] == 'FAIL':
        failing.append(f"AHU TnT: {wo['ahu']:.1f}% (needs ≥90%)")
    
    if not failing:
        failing.append(f"PM Score: {wo['pm_score']:.1f}% (needs ≥90%)")
    
    notes = f"WTW FY26 - Reopening: Store not meeting PM criteria. "
    notes += "Failing: " + ", ".join(failing)
    notes += f". Current PM Score: {wo['pm_score']:.1f}%"
    
    return notes

def try_reopen_wo(page, wo):
    """Attempt to reopen a work order"""
    
    # Step 1: Find and click "Edit Work Order" button
    edit_selectors = [
        'button:has-text("Edit Work Order")',
        'a:has-text("Edit Work Order")',
        'button:has-text("Edit")',
        '[data-action="edit"]',
        '.edit-wo-button',
        'button.edit',
        '#editWorkOrder',
        'a.edit-link',
    ]
    
    edit_found = False
    for selector in edit_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=2000):
                print("        📝 Found 'Edit Work Order' button, clicking...")
                btn.click()
                edit_found = True
                time.sleep(2)  # Wait for edit mode
                break
        except:
            pass
    
    if not edit_found:
        print("        ⚠️  Could not find 'Edit Work Order' button")
        return False
    
    # Step 2: Find status dropdown and change to "In Progress"
    status_selectors = [
        'select[name*="status"]',
        'select#status',
        'select.status-dropdown',
        '[data-field="status"] select',
        'select:has-text("Completed")',
    ]
    
    status_found = False
    for selector in status_selectors:
        try:
            dropdown = page.locator(selector).first
            if dropdown.is_visible(timeout=2000):
                print("        📋 Found status dropdown, changing to 'In Progress'...")
                dropdown.select_option(label='In Progress')
                status_found = True
                time.sleep(1)
                break
        except:
            pass
    
    if not status_found:
        # Try clicking on a status field that might open a dropdown
        try:
            page.locator('text=Completed').first.click()
            time.sleep(1)
            page.locator('text=In Progress').first.click()
            status_found = True
            print("        📋 Changed status via click")
        except:
            print("        ⚠️  Could not find/change status dropdown")
            return False
    
    # Step 3: Add notes
    notes = generate_reopen_notes(wo)
    notes_selectors = [
        'textarea[name*="note"]',
        'textarea#notes',
        'textarea.notes',
        '[data-field="notes"] textarea',
        'textarea[placeholder*="note"]',
        'textarea',
    ]
    
    notes_found = False
    for selector in notes_selectors:
        try:
            textarea = page.locator(selector).first
            if textarea.is_visible(timeout=2000):
                print(f"        📝 Adding notes: {notes[:50]}...")
                textarea.fill(notes)
                notes_found = True
                time.sleep(1)
                break
        except:
            pass
    
    if not notes_found:
        print("        ⚠️  Could not find notes field (continuing anyway)")
    
    # Step 4: Save
    save_selectors = [
        'button:has-text("Save")',
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Update")',
        '.save-button',
        '#saveButton',
    ]
    
    save_found = False
    for selector in save_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=2000):
                print("        💾 Found Save button, clicking...")
                btn.click()
                save_found = True
                time.sleep(2)
                break
        except:
            pass
    
    if not save_found:
        print("        ⚠️  Could not find Save button")
        return False
    
    print("        ✅ Work order updated!")
    return True

def main():
    print("🔧 Service Channel Reopen Helper")
    print("="*60)
    print("")
    print("Workflow:")
    print("  1. Click 'Edit Work Order' button")
    print("  2. Change status dropdown: Completed → In Progress")
    print("  3. Add notes about failing criteria")
    print("  4. Save")
    print("="*60)
    
    # Load WOs
    wos = load_critical_reopen_wos()
    print(f"\n📋 Found {len(wos)} work orders that need reopening")
    print(f"   (Completed + PM < 90% + not Div1)\n")
    
    # Show first 10
    print("Sample of WOs to reopen:")
    print("-" * 80)
    print(f"{'Store':<8} {'City':<20} {'PM':<8} {'TnT':<10} {'Rack':<10} {'AHU':<10}")
    print("-" * 80)
    for wo in wos[:10]:
        tnt_flag = '❌' if wo['tnt_pass'] == 'FAIL' else '✓'
        rack_flag = '❌' if wo['rack_pass'] == 'FAIL' else '✓'
        ahu_flag = '❌' if wo['ahu_pass'] == 'FAIL' else '✓'
        print(f"{wo['store']:<8} {wo['city'][:18]:<20} {wo['pm_score']:<8.1f} {tnt_flag}{wo['tnt']:<9.1f} {rack_flag}{wo['rack']:<9.1f} {ahu_flag}{wo['ahu']:<9.1f}")
    print("-" * 80)
    
    print("\n" + "="*60)
    print("\n🌐 Opening Chrome...")
    print("   1. Log into Service Channel when prompted")
    print("   2. Press Enter here when ready to start")
    print("\n")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel='chrome',
            headless=False,
            slow_mo=300  # Slow down for visibility
        )
        
        context = browser.new_context(
            viewport={'width': 1400, 'height': 900}
        )
        page = context.new_page()
        
        # Go to Service Channel login
        page.goto('https://www.servicechannel.com/sc/login')
        
        input("\n👆 Log into Service Channel, then press Enter here to continue...")
        
        print("\n🚀 Starting WO processing...")
        print("   Commands: [Enter]=auto-try  [m]=manual  [s]=skip  [q]=quit\n")
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for i, wo in enumerate(wos):
            url = f"{SC_URL}{wo['tracking']}"
            notes = generate_reopen_notes(wo)
            
            print(f"\n{'='*60}")
            print(f"[{i+1}/{len(wos)}] Store {wo['store']} - {wo['city']}, {wo['state']}")
            print(f"  Tracking: {wo['tracking']}")
            print(f"  PM Score: {wo['pm_score']:.1f}%")
            print(f"  TnT: {wo['tnt']:.1f}% {'❌' if wo['tnt_pass']=='FAIL' else '✓'}")
            print(f"  Rack: {wo['rack']:.1f}% {'❌' if wo['rack_pass']=='FAIL' else '✓'}")
            print(f"  AHU: {wo['ahu']:.1f}% {'❌' if wo['ahu_pass']=='FAIL' else '✓'}")
            print(f"  Notes: {notes}")
            print(f"  URL: {url}")
            
            # Navigate to WO
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                time.sleep(2)  # Wait for page to load fully
            except Exception as e:
                print(f"  ❌ Error loading page: {e}")
                fail_count += 1
                continue
            
            # Wait for user input
            action = input("  Action [Enter=auto, m=manual, s=skip, q=quit]: ").strip().lower()
            
            if action == 'q':
                print("\n👋 Quitting...")
                break
            elif action == 's':
                print("  ⏭️  Skipped")
                skip_count += 1
                continue
            elif action == 'm':
                print("  👆 Do it manually, then press Enter when done...")
                input()
                success_count += 1
                continue
            else:
                # Try automatic reopen
                if try_reopen_wo(page, wo):
                    success_count += 1
                else:
                    print("  ⚠️  Auto-reopen failed. Try manually (m) or skip (s)?")
                    retry = input("  ").strip().lower()
                    if retry == 'm':
                        print("  👆 Do it manually, then press Enter when done...")
                        input()
                        success_count += 1
                    else:
                        fail_count += 1
        
        print("\n" + "="*60)
        print("📊 Summary")
        print("="*60)
        print(f"  ✅ Success: {success_count}")
        print(f"  ⏭️  Skipped: {skip_count}")
        print(f"  ❌ Failed: {fail_count}")
        print(f"  📋 Remaining: {len(wos) - i - 1}")
        print("="*60)
        
        input("\nPress Enter to close browser...")
        browser.close()

if __name__ == '__main__':
    main()
