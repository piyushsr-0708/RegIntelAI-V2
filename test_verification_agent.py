"""Temporary test to verify Verification Agent functionality"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.database.services.verification_agent_service import VerificationAgentService

def test_agent_decision():
    """Test agent decision making with real dataset"""
    agent = VerificationAgentService(project_root)
    
    # Test with MD10190 (known document from datasets)
    print("Testing Verification Agent with MD10190...")
    
    # Test 1: Low criticality requirement
    decision = agent.decide_verification_strategy(
        document_id="MD10190",
        requirement_id="MD10190_req5",
        criticality="LOW",
        department="Compliance"
    )
    
    print(f"\n--- Test 1: Low Criticality ---")
    print(f"Verdict: {decision.verdict}")
    print(f"Reasoning: {decision.reasoning}")
    print(f"Confidence: {decision.confidence_score:.2f}")
    print(f"Gates: {decision.gates_evaluated}")
    
    # Test 2: Critical requirement
    decision = agent.decide_verification_strategy(
        document_id="MD10190",
        requirement_id="MD10190_req9",
        criticality="CRITICAL",
        department="Treasury"
    )
    
    print(f"\n--- Test 2: Critical Requirement ---")
    print(f"Verdict: {decision.verdict}")
    print(f"Reasoning: {decision.reasoning}")
    print(f"Confidence: {decision.confidence_score:.2f}")
    print(f"Gates: {decision.gates_evaluated}")
    
    # Test 3: Non-existent document (should NO_GO)
    decision = agent.decide_verification_strategy(
        document_id="NONEXISTENT",
        requirement_id=None,
        criticality="MEDIUM",
        department="Compliance"
    )
    
    print(f"\n--- Test 3: Non-existent Document ---")
    print(f"Verdict: {decision.verdict}")
    print(f"Reasoning: {decision.reasoning}")
    print(f"Confidence: {decision.confidence_score:.2f}")
    print(f"Gates: {decision.gates_evaluated}")
    
    print("\n✓ All tests completed successfully")
    return True

if __name__ == "__main__":
    try:
        success = test_agent_decision()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
