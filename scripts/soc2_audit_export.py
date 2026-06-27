#!/usr/bin/env python3
import os
import sys
import csv
import asyncio
import hashlib
from datetime import datetime

# Setup path so we can import aegis_backend
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aegis_backend.database import AsyncSessionLocal, AuditLog

async def export_and_verify_soc2_audit(output_csv: str):
    print(f"Starting SOC2 Type II Audit Log Extraction...")
    
    async with AsyncSessionLocal() as db:
        stmt = select(AuditLog).order_by(AuditLog.id.asc())
        res = await db.execute(stmt)
        logs = res.scalars().all()
        
        if not logs:
            print("No audit logs found in the system.")
            return

        print(f"Found {len(logs)} audit log entries. Verifying cryptographic integrity...")
        
        tampered_count = 0
        prev_hash = "GENESIS"
        chain_started = False
        
        verified_logs = []

        for log in logs:
            status = "VERIFIED"
            if not log.entry_hash:
                if chain_started:
                    status = "TAMPERED - MISSING HASH"
                    tampered_count += 1
                else:
                    status = "UNHASHED (LEGACY)"
            else:
                chain_started = True
                hash_input = f"{log.user_email}|{log.action}|{log.target_type}|{log.target_id or ''}|{log.details or ''}|{prev_hash}"
                computed = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
                
                if log.entry_hash != computed:
                    status = "TAMPERED - HASH MISMATCH"
                    tampered_count += 1
                prev_hash = log.entry_hash
            
            verified_logs.append({
                "ID": log.id,
                "Timestamp (UTC)": log.timestamp.isoformat(),
                "User Email": log.user_email,
                "Action": log.action,
                "Target Type": log.target_type,
                "Target ID": log.target_id,
                "Details": log.details,
                "Integrity Status": status,
                "Entry Hash": log.entry_hash
            })

        print(f"Integrity check complete. Tampered records found: {tampered_count}")
        
        with open(output_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=verified_logs[0].keys())
            writer.writeheader()
            writer.writerows(verified_logs)
            
        print(f"SOC2 Audit Report successfully exported to: {output_csv}")
        
        if tampered_count > 0:
            print("WARNING: AUDIT TRAIL COMPROMISED. DO NOT SUBMIT TO SOC2 AUDITORS WITHOUT INVESTIGATION.")
            sys.exit(1)
        else:
            print("Audit trail is mathematically verified and ready for SOC2 compliance submission.")

if __name__ == "__main__":
    output_filename = f"soc2_audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    output_path = os.path.join(parent_dir, output_filename)
    asyncio.run(export_and_verify_soc2_audit(output_path))
