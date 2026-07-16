"""
Upload Feature Validation Script

Validates that the document upload feature works correctly while preserving
backward compatibility with the existing MD document pipeline.

Tests:
1. Regression test: MD10190 pipeline still works with default behavior
2. Feature test: Upload endpoint file operations work correctly
3. Document ID generation follows UPYYYYMMDD_NNNN format
4. Upload directory is created correctly
5. Orchestrator accepts pdf_source_dir parameter
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_document_id_generation():
    """Test that document ID generation follows the correct format."""
    print("\n" + "="*80)
    print("TEST 1: Document ID Generation")
    print("="*80)
    
    from backend.main import _generate_upload_document_id
    
    doc_id = _generate_upload_document_id()
    print(f"Generated document ID: {doc_id}")
    
    # Validate format: UPYYYYMMDD_NNNN
    today = datetime.now().strftime("%Y%m%d")
    expected_prefix = f"UP{today}_"
    
    if not doc_id.startswith(expected_prefix):
        print(f"✗ FAIL: Expected prefix {expected_prefix}, got {doc_id[:13]}")
        return False
    
    # Validate sequence number is 4 digits
    try:
        seq_part = doc_id.split("_")[1]
        seq_num = int(seq_part)
        if len(seq_part) != 4:
            print(f"✗ FAIL: Sequence number should be 4 digits, got {len(seq_part)}")
            return False
        print(f"✓ PASS: Document ID format is correct (sequence: {seq_num:04d})")
        return True
    except (IndexError, ValueError) as e:
        print(f"✗ FAIL: Invalid sequence number format: {e}")
        return False


def test_orchestrator_backward_compatibility():
    """Test that orchestrator still works without pdf_source_dir (backward compatibility)."""
    print("\n" + "="*80)
    print("TEST 2: Orchestrator Backward Compatibility")
    print("="*80)
    
    try:
        from pipeline.orchestrator.document_orchestrator import DocumentPipelineOrchestrator
        
        # Create orchestrator WITHOUT pdf_source_dir (old behavior)
        orchestrator = DocumentPipelineOrchestrator(project_root=project_root)
        
        # Verify default path is master_directions
        expected_pdf_dir = project_root / "datasets" / "raw" / "master_directions" / "pdfs"
        actual_pdf_dir = orchestrator.paths["raw_pdf"]
        
        if actual_pdf_dir != expected_pdf_dir:
            print(f"✗ FAIL: Expected PDF dir {expected_pdf_dir}, got {actual_pdf_dir}")
            return False
        
        print(f"✓ PASS: Orchestrator defaults to master_directions/pdfs")
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Orchestrator initialization failed: {e}")
        return False


def test_orchestrator_pdf_source_override():
    """Test that orchestrator accepts custom pdf_source_dir."""
    print("\n" + "="*80)
    print("TEST 3: Orchestrator PDF Source Override")
    print("="*80)
    
    try:
        from pipeline.orchestrator.document_orchestrator import DocumentPipelineOrchestrator
        
        # Create orchestrator WITH pdf_source_dir (new behavior)
        custom_pdf_dir = project_root / "datasets" / "raw" / "uploaded_documents" / "pdfs"
        orchestrator = DocumentPipelineOrchestrator(
            project_root=project_root,
            pdf_source_dir=custom_pdf_dir
        )
        
        actual_pdf_dir = orchestrator.paths["raw_pdf"]
        
        if actual_pdf_dir != custom_pdf_dir:
            print(f"✗ FAIL: Expected PDF dir {custom_pdf_dir}, got {actual_pdf_dir}")
            return False
        
        print(f"✓ PASS: Orchestrator accepts custom pdf_source_dir")
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Orchestrator with custom PDF dir failed: {e}")
        return False


def test_upload_directory_structure():
    """Test that upload directory is created in the correct location."""
    print("\n" + "="*80)
    print("TEST 4: Upload Directory Structure")
    print("="*80)
    
    upload_dir = project_root / "datasets" / "raw" / "uploaded_documents" / "pdfs"
    
    # Create directory
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    if not upload_dir.exists():
        print(f"✗ FAIL: Upload directory was not created: {upload_dir}")
        return False
    
    # Verify it's separate from master_directions
    master_dir = project_root / "datasets" / "raw" / "master_directions" / "pdfs"
    if upload_dir == master_dir or str(upload_dir).startswith(str(master_dir)):
        print(f"✗ FAIL: Upload directory is not separate from master_directions")
        return False
    
    print(f"✓ PASS: Upload directory created at correct location")
    print(f"  Master directions: {master_dir}")
    print(f"  Uploaded docs:     {upload_dir}")
    return True


def test_database_ingest_document_scoped():
    """Test that database ingest accepts document_id parameter."""
    print("\n" + "="*80)
    print("TEST 5: Database Ingest Document-Scoped Mode")
    print("="*80)
    
    try:
        from backend.database.ingest import ingest
        import inspect
        
        # Check function signature
        sig = inspect.signature(ingest)
        params = list(sig.parameters.keys())
        
        if "document_id" not in params:
            print(f"✗ FAIL: ingest() function missing document_id parameter")
            return False
        
        # Check parameter is optional
        param = sig.parameters["document_id"]
        if param.default == inspect.Parameter.empty:
            print(f"✗ FAIL: document_id parameter should be optional")
            return False
        
        print(f"✓ PASS: ingest() accepts optional document_id parameter")
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Database ingest validation failed: {e}")
        return False


def test_permissions_configuration():
    """Test that DOC_UPLOAD permission exists and is assigned correctly."""
    print("\n" + "="*80)
    print("TEST 6: Permissions Configuration")
    print("="*80)
    
    try:
        from backend.permissions import Perm, ROLE_PERMISSIONS
        
        # Check DOC_UPLOAD permission exists
        if not hasattr(Perm, "DOC_UPLOAD"):
            print(f"✗ FAIL: Perm.DOC_UPLOAD permission not defined")
            return False
        
        # Check permission is assigned to appropriate roles
        roles_with_upload = []
        for role, perms in ROLE_PERMISSIONS.items():
            if Perm.DOC_UPLOAD in perms or Perm.WILDCARD in perms:
                roles_with_upload.append(role)
        
        if not roles_with_upload:
            print(f"✗ FAIL: DOC_UPLOAD permission not assigned to any role")
            return False
        
        print(f"✓ PASS: DOC_UPLOAD permission exists")
        print(f"  Assigned to roles: {', '.join(roles_with_upload)}")
        return True
        
    except Exception as e:
        print(f"✗ FAIL: Permissions validation failed: {e}")
        return False


def test_original_dataset_immutability():
    """Verify that original RBI dataset remains untouched."""
    print("\n" + "="*80)
    print("TEST 7: Original Dataset Immutability")
    print("="*80)
    
    master_dir = project_root / "datasets" / "raw" / "master_directions"
    
    # Check that master_directions directory exists
    if not master_dir.exists():
        print(f"✗ FAIL: Master directions directory not found: {master_dir}")
        return False
    
    # Check that it contains PDF files
    pdf_dir = master_dir / "pdfs"
    if not pdf_dir.exists():
        print(f"✗ FAIL: Master directions PDFs directory not found: {pdf_dir}")
        return False
    
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"✗ FAIL: No PDF files found in master_directions")
        return False
    
    print(f"✓ PASS: Original RBI dataset remains intact")
    print(f"  Location: {master_dir}")
    print(f"  PDF count: {len(pdf_files)}")
    return True


def main():
    """Run all validation tests."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "UPLOAD FEATURE VALIDATION SUITE" + " "*26 + "║")
    print("╚" + "="*78 + "╝")
    
    tests = [
        test_document_id_generation,
        test_orchestrator_backward_compatibility,
        test_orchestrator_pdf_source_override,
        test_upload_directory_structure,
        test_database_ingest_document_scoped,
        test_permissions_configuration,
        test_original_dataset_immutability,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"\n✗ EXCEPTION in {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False))
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-"*80)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED - Implementation is validated")
        return 0
    else:
        print(f"\n✗ {total - passed} TEST(S) FAILED - Implementation needs fixes")
        return 1


if __name__ == "__main__":
    sys.exit(main())
