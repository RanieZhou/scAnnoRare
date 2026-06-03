import os
import sys
import time
import json
import subprocess
import requests

def run_tests():
    print("=====================================================")
    print("[START] Starting scAnnoRare Auto Integration Test Suite...")
    print("=====================================================")
    
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    local_agent_dir = os.path.dirname(workspace_dir)
    
    # 1. Start local-agent FastAPI server in background
    print("\n[Step 1] Starting Local Agent FastAPI server in background...")
    proc = subprocess.Popen(
        ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "17890"],
        cwd=local_agent_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to boot
    time.sleep(3.0)
    
    # Check if server is running
    if proc.poll() is not None:
        print("[ERROR] Local Agent failed to start. stdout/stderr:")
        stdout, stderr = proc.communicate()
        print(stderr.decode("utf-8"))
        return False
        
    print("[SUCCESS] Local Agent successfully listening on http://127.0.0.1:17890")
    
    agent_url = "http://127.0.0.1:17890"
    session_token = None
    
    try:
        # 2. Test GET /api/v1/local/health (Unpaired)
        print("\n[Step 2] Testing /api/v1/local/health...")
        r = requests.get(f"{agent_url}/api/v1/local/health")
        print(f"Response: {r.status_code} | Paired: {r.json().get('paired')}")
        assert r.status_code == 200
        
        # 3. Generate Pairing Code
        print("\n[Step 3] Generating pairing code from Admin Console...")
        r = requests.post(f"{agent_url}/api/v1/local/admin/generate-pairing-code")
        print(f"Response: {r.status_code} | Code: {r.json().get('pairing_code')}")
        assert r.status_code == 200
        pairing_code = r.json().get("pairing_code")
        
        # 4. Perform Pairing MATCH (Simulate frontend PNA request)
        print("\n[Step 4] Triggering pairing validation...")
        payload = {"pairing_code": pairing_code, "origin": "http://localhost:5173"}
        r = requests.post(f"{agent_url}/api/v1/local/pair", json=payload)
        print(f"Response: {r.status_code} | Token received: {r.json().get('session_token') is not None}")
        assert r.status_code == 200
        session_token = r.json().get("session_token")
        
        headers = {"Authorization": f"Bearer {session_token}", "X-scAnnoRare-Origin": "http://localhost:5173"}
        
        # 5. Check Environment Diagnostics
        print("\n[Step 5] Checking Environment diagnostics...")
        r = requests.get(f"{agent_url}/api/v1/local/env", headers=headers)
        print(f"Response: {r.status_code}")
        env = r.json()
        print(f"  OS: {env.get('os')} | CPU: {env.get('cpu_count')} | GPU available: {env.get('gpu_available')}")
        print(f"  Packages version: {env.get('packages')}")
        assert r.status_code == 200
        
        # 6. Test File Selection (.h5ad)
        print("\n[Step 6] Testing file selection validation...")
        h5ad_path = os.path.join(workspace_dir, "datasets", "tiny_dataset.h5ad")
        r = requests.post(f"{agent_url}/api/v1/local/files/select", json={"filepath": h5ad_path}, headers=headers)
        print(f"Response: {r.status_code}")
        meta = r.json()
        print(f"  Cells found: {meta.get('n_cells')} | Genes found: {meta.get('n_genes')}")
        assert r.status_code == 200
        
        # 7. Test Dataset registry & label counts
        print("\n[Step 7] Testing dataset registration analysis...")
        payload_reg = {
            "filepath": h5ad_path,
            "dataset_name": "tiny_test_data",
            "label_col": "cell_type",
            "batch_col": "batch",
            "rare_threshold": 0.05
        }
        r = requests.post(f"{agent_url}/api/v1/local/files/register-dataset", json=payload_reg, headers=headers)
        print(f"Response: {r.status_code}")
        summary = r.json().get("summary")
        print(f"  Valid cells: {summary.get('valid_label_cells')} | Rare candidates: {[item.get('class_name') for item in summary.get('rare_candidates')]}")
        assert r.status_code == 200
        
        # 8. Test Asynchronous evaluation runner (Annotation)
        print("\n[Step 8] Triggering cell type annotation precision evaluation...")
        pred_csv = os.path.join(workspace_dir, "predictions", "imported_predictions", "tiny_predictions.csv")
        payload_task = {
            "filepath": h5ad_path,
            "pred_csv_path": pred_csv,
            "label_col": "cell_type",
            "match_mode": "relaxed"
        }
        r = requests.post(f"{agent_url}/api/v1/local/tasks/evaluate-annotation", json=payload_task, headers=headers)
        print(f"Response: {r.status_code}")
        assert r.status_code == 200
        local_job_id = r.json().get("local_job_id")
        print(f"  Task generated: {local_job_id}")
        
        # 9. Poll Task until completion
        print("\n[Step 9] Polling task progress...")
        completed = False
        for attempt in range(15):
            r = requests.get(f"{agent_url}/api/v1/local/tasks/{local_job_id}", headers=headers)
            job = r.json()
            print(f"  Attempt {attempt + 1}: Status={job.get('status')} | Progress={job.get('progress')}%")
            if job.get("status") in ["success", "failed"]:
                completed = True
                result = job.get("result")
                print(f"  Task finished. Success: {result.get('success', False) if result else False}")
                if result and result.get("success"):
                    print(f"  Overall Metrics: {result.get('overall_metrics')}")
                elif result:
                    print(f"  Error trace: {result.get('error')}")
                break
            time.sleep(1.5)
            
        assert completed
        assert job.get("status") == "success"
        
        # 10. Check html report generation
        print("\n[Step 10] Validating HTML report accessibility...")
        report_path = os.path.join(workspace_dir, "jobs", local_job_id, "report.html")
        print(f"  Expecting report at: {report_path}")
        assert os.path.exists(report_path)
        print("  [SUCCESS] HTML offline report exists on disk!")
        
        print("\n=====================================================")
        print("[SUCCESS] All scAnnoRare tests passed flawlessly!")
        print("=====================================================")
        return True
        
    except AssertionError as e:
        print(f"\n[ASSERTION ERROR] Test failed.")
        return False
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}")
        return False
    finally:
        # Gracefully shutdown uvicorn
        print("\n[Cleanup] Shutting down Local Agent background server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
            print("[SUCCESS] Server terminated successfully.")
        except subprocess.TimeoutExpired:
            proc.kill()
            print("[WARNING] Server killed forcefully.")

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
